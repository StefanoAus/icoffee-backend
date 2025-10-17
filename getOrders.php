<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$date = $_GET['date'] ?? date("Y-m-d");
$orders = read_json_file(ORDERS_FILE);
if (!is_array($orders)) $orders = [];

$list = $orders[$date] ?? [];

$requestedGroup = trim($_GET['group'] ?? '');
$role = $_GET['role'] ?? 'user';

if ($role !== 'admin') {
  if ($requestedGroup === '') {
    http_response_code(400);
    echo json_encode(["success" => false, "message" => "Gruppo richiesto mancante"]);
    exit;
  }
  $list = array_values(array_filter($list, function ($item) use ($requestedGroup) {
    return $item['group'] === $requestedGroup;
  }));
} elseif ($requestedGroup !== '') {
  $list = array_values(array_filter($list, function ($item) use ($requestedGroup) {
    return $item['group'] === $requestedGroup;
  }));
}

// ordina per gruppo poi per username
usort($list, function($a, $b){
  $g = strcmp($a['group'], $b['group']);
  if ($g !== 0) return $g;
  return strcmp($a['username'], $b['username']);
});

function normalize_order_payload($order) {
  $normalized = [];
  if (is_array($order)) {
    if (isset($order['drink']) && is_array($order['drink'])) {
      $item = trim((string)($order['drink']['item'] ?? ''));
      $variant = trim((string)($order['drink']['variant'] ?? ''));
      if ($item !== '' && $variant !== '') {
        $normalized['drink'] = ['item' => $item, 'variant' => $variant];
      }
    }
    if (isset($order['food']) && is_array($order['food'])) {
      $item = trim((string)($order['food']['item'] ?? ''));
      $variant = trim((string)($order['food']['variant'] ?? ''));
      if ($item !== '' && $variant !== '') {
        $normalized['food'] = ['item' => $item, 'variant' => $variant];
      }
    }
    if (isset($order['legacyText'])) {
      $legacy = trim((string)$order['legacyText']);
      if ($legacy !== '') {
        $normalized['legacyText'] = $legacy;
      }
    }
    if (!empty($normalized)) {
      return $normalized;
    }
  }

  if (is_string($order)) {
    $text = trim($order);
    if ($text !== '') {
      return ['legacyText' => $text];
    }
  }

  return $normalized;
}

$list = array_map(function ($entry) {
  $entry['order'] = normalize_order_payload($entry['order'] ?? null);
  return $entry;
}, $list);

echo json_encode($list, JSON_UNESCAPED_UNICODE);
