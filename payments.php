<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$method = $_SERVER['REQUEST_METHOD'];
$users = read_json_file(USERS_FILE);
if (!is_array($users)) $users = [];

$payments = read_json_file(PAYMENTS_FILE);
if (!is_array($payments)) $payments = [];

function get_user_by_username($users, $username) {
  foreach ($users as $user) {
    if (($user['username'] ?? '') === $username) {
      return $user;
    }
  }
  return null;
}

function ensure_group_access($users, $group, $username) {
  $user = get_user_by_username($users, $username);
  if (!$user || ($user['group'] ?? '') !== $group) {
    http_response_code(403);
    echo json_encode(["success" => false, "message" => "Accesso non consentito al gruppo richiesto"]);
    exit;
  }
  return $user;
}

switch ($method) {
  case 'GET':
    $group = trim($_GET['group'] ?? '');
    $role = $_GET['role'] ?? 'user';
    $username = trim($_GET['username'] ?? '');
    $date = trim($_GET['date'] ?? '');
    if ($date === '') {
      $date = date('Y-m-d');
    }

    if ($group === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Gruppo richiesto mancante"]);
      exit;
    }

    if ($role !== 'admin') {
      if ($username === '') {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Utente richiesto mancante"]);
        exit;
      }
      ensure_group_access($users, $group, $username);
    }

    $groupMembers = [];
    foreach ($users as $user) {
      if (($user['group'] ?? '') === $group) {
        $groupMembers[] = $user['username'];
      }
    }

    $counts = [];
    foreach ($groupMembers as $member) {
      $counts[$member] = 0;
    }

    $log = [];
    foreach ($payments as $paymentDate => $groups) {
      if (!is_array($groups)) continue;
      $payer = trim((string)($groups[$group] ?? ''));
      if ($payer === '') continue;
      $counts[$payer] = ($counts[$payer] ?? 0) + 1;
      $log[] = ['date' => $paymentDate, 'username' => $payer];
    }

    usort($log, function ($a, $b) {
      return strcmp($b['date'], $a['date']);
    });

    $history = [];
    foreach ($counts as $member => $count) {
      $history[] = ['username' => $member, 'count' => $count];
    }

    usort($history, function ($a, $b) {
      if ($a['count'] === $b['count']) {
        return strcmp($a['username'], $b['username']);
      }
      return $b['count'] <=> $a['count'];
    });

    $payerForDate = null;
    if (isset($payments[$date]) && is_array($payments[$date])) {
      $recorded = trim((string)($payments[$date][$group] ?? ''));
      if ($recorded !== '') {
        $payerForDate = ['username' => $recorded, 'date' => $date];
      }
    }

    echo json_encode([
      "success" => true,
      "group" => $group,
      "date" => $date,
      "payer" => $payerForDate,
      "totals" => $history,
      "log" => $log
    ], JSON_UNESCAPED_UNICODE);
    break;

  case 'POST':
    $raw = file_get_contents('php://input');
    $payload = json_decode($raw, true);
    if (!is_array($payload)) $payload = [];

    $group = trim($payload['group'] ?? '');
    $payer = trim($payload['payer'] ?? '');
    $date = trim($payload['date'] ?? '');
    $role = $payload['role'] ?? 'user';
    $actor = trim($payload['actor'] ?? '');

    if ($date === '') {
      $date = date('Y-m-d');
    }

    if ($group === '' || $payer === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Dati mancanti o non validi per il pagamento"]);
      exit;
    }

    $payerUser = get_user_by_username($users, $payer);
    if (!$payerUser) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Utente non trovato"]);
      exit;
    }

    if (($payerUser['group'] ?? '') !== $group) {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "L'utente selezionato non appartiene al gruppo"]);
      exit;
    }

    if ($role !== 'admin') {
      if ($actor === '') {
        $actor = $payer;
      }
      ensure_group_access($users, $group, $actor);
      if ($actor !== $payer) {
        http_response_code(403);
        echo json_encode(["success" => false, "message" => "Non puoi registrare il pagamento per un altro utente"]);
        exit;
      }
    }

    if (!isset($payments[$date]) || !is_array($payments[$date])) {
      $payments[$date] = [];
    }
    $payments[$date][$group] = $payer;

    if (!write_json_file(PAYMENTS_FILE, $payments)) {
      http_response_code(500);
      echo json_encode(["success" => false, "message" => "Impossibile salvare il pagamento"]);
      exit;
    }

    echo json_encode(["success" => true]);
    break;

  default:
    http_response_code(405);
    echo json_encode(["success" => false, "message" => "Metodo non supportato"]);
}
