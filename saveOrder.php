<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$payload = json_decode(file_get_contents('php://input'), true);
$username = trim($payload['username'] ?? '');
$group = trim($payload['group'] ?? '');
$orderPayload = $payload['order'] ?? null;
$date = date("Y-m-d");

$drinkItem = '';
$drinkVariant = '';
$foodItem = '';
$foodVariant = '';

if (is_array($orderPayload)) {
  $drinkPayload = $orderPayload['drink'] ?? null;
  if (is_array($drinkPayload)) {
    $drinkItem = trim((string)($drinkPayload['item'] ?? ''));
    $drinkVariant = trim((string)($drinkPayload['variant'] ?? ''));
  }
  $foodPayload = $orderPayload['food'] ?? null;
  if (is_array($foodPayload)) {
    $foodItem = trim((string)($foodPayload['item'] ?? ''));
    $foodVariant = trim((string)($foodPayload['variant'] ?? ''));
  }
}

if ($username === '' || $group === '') {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "Dati mancanti o non validi per l'ordine"]);
  exit;
}

$hasDrink = ($drinkItem !== '' && $drinkVariant !== '');
$hasFood = ($foodItem !== '' && $foodVariant !== '');

if (!$hasDrink && !$hasFood) {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "Seleziona almeno una bevanda o un cibo"]);
  exit;
}

$menu = read_json_file(MENU_FILE);
if (!is_array($menu)) {
  $menu = ['drinks' => [], 'foods' => []];
}

function choice_exists($list, $itemName, $variant) {
  if (!is_array($list)) return false;
  foreach ($list as $entry) {
    if (!is_array($entry)) continue;
    $name = trim((string)($entry['name'] ?? ''));
    if ($name !== $itemName) continue;
    $options = $entry['options'] ?? [];
    if (!is_array($options)) return false;
    foreach ($options as $opt) {
      if (trim((string)$opt) === $variant) {
        return true;
      }
    }
    return false;
  }
  return false;
}

if ($hasDrink && !choice_exists($menu['drinks'] ?? [], $drinkItem, $drinkVariant)) {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "La voce selezionata non è più disponibile"]);
  exit;
}

if ($hasFood && !choice_exists($menu['foods'] ?? [], $foodItem, $foodVariant)) {
  http_response_code(400);
  echo json_encode(["success" => false, "message" => "La voce selezionata non è più disponibile"]);
  exit;
}

$orders = read_json_file(ORDERS_FILE);
if (!is_array($orders)) $orders = [];

if (!isset($orders[$date])) $orders[$date] = [];

// Se l'utente ha già inserito un ordine oggi, lo sovrascriviamo
$orderData = [];
if ($hasDrink) {
  $orderData['drink'] = ['item' => $drinkItem, 'variant' => $drinkVariant];
}
if ($hasFood) {
  $orderData['food'] = ['item' => $foodItem, 'variant' => $foodVariant];
}

$updated = false;
for ($i=0; $i<count($orders[$date]); $i++) {
  if ($orders[$date][$i]['username'] === $username) {
    $orders[$date][$i]['order'] = $orderData;
    $orders[$date][$i]['group'] = $group;
    $updated = true;
    break;
  }
}
if (!$updated) {
  $orders[$date][] = [
    "username" => $username,
    "group" => $group,
    "order" => $orderData
  ];
}

write_json_file(ORDERS_FILE, $orders);
echo json_encode(["success" => true]);
