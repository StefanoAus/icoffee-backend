<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$method = $_SERVER['REQUEST_METHOD'];
$payload = null;
if ($method !== 'GET') {
  $raw = file_get_contents('php://input');
  $payload = json_decode($raw, true);
  if (!is_array($payload)) $payload = [];
}

$actorRole = $method === 'GET' ? ($_GET['role'] ?? 'user') : ($payload['actorRole'] ?? 'user');
if ($actorRole !== 'admin') {
  http_response_code(403);
  echo json_encode(["success" => false, "message" => "Operazione permessa solo agli amministratori"]);
  exit;
}

$groups = read_json_file(GROUPS_FILE);
if (!is_array($groups)) $groups = [];

function normalize_groups($groups) {
  $normalized = [];
  foreach ($groups as $group) {
    if (!is_string($group)) continue;
    $trimmed = trim($group);
    if ($trimmed === '') continue;
    if (!in_array($trimmed, $normalized, true)) {
      $normalized[] = $trimmed;
    }
  }
  return $normalized;
}

function persist_groups($groups) {
  if (!write_json_file(GROUPS_FILE, array_values($groups))) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Impossibile salvare i gruppi"]);
    exit;
  }
}

function persist_users_list($users) {
  if (!write_json_file(USERS_FILE, $users)) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Impossibile aggiornare gli utenti"]);
    exit;
  }
}

switch ($method) {
  case 'GET':
    echo json_encode(["success" => true, "groups" => array_values($groups)], JSON_UNESCAPED_UNICODE);
    break;

  case 'POST':
    $name = trim((string)($payload['name'] ?? ''));
    if ($name === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Il nome del gruppo è obbligatorio"]);
      exit;
    }
    if (in_array($name, $groups, true)) {
      http_response_code(409);
      echo json_encode(["success" => false, "message" => "Esiste già un gruppo con questo nome"]);
      exit;
    }
    $groups[] = $name;
    persist_groups($groups);
    echo json_encode(["success" => true]);
    break;

  case 'PUT':
    $oldName = trim((string)($payload['oldName'] ?? ''));
    $newName = trim((string)($payload['newName'] ?? ''));
    if ($oldName === '' || $newName === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Specificare i nomi del gruppo da modificare"]);
      exit;
    }
    if (!in_array($oldName, $groups, true)) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Gruppo non trovato"]);
      exit;
    }
    if ($oldName === $newName) {
      echo json_encode(["success" => true]);
      exit;
    }
    if (in_array($newName, $groups, true)) {
      http_response_code(409);
      echo json_encode(["success" => false, "message" => "Esiste già un gruppo con il nuovo nome"]);
      exit;
    }
    $users = read_json_file(USERS_FILE);
    if (!is_array($users)) $users = [];
    for ($i = 0; $i < count($users); $i++) {
      if (($users[$i]['group'] ?? '') === $oldName) {
        $users[$i]['group'] = $newName;
      }
    }
    persist_users_list($users);
    for ($i = 0; $i < count($groups); $i++) {
      if ($groups[$i] === $oldName) {
        $groups[$i] = $newName;
        break;
      }
    }
    $groups = normalize_groups($groups);
    persist_groups($groups);
    echo json_encode(["success" => true]);
    break;

  case 'DELETE':
    $name = trim((string)($payload['name'] ?? ''));
    if ($name === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Specificare il gruppo da eliminare"]);
      exit;
    }
    if (!in_array($name, $groups, true)) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Gruppo non trovato"]);
      exit;
    }
    $users = read_json_file(USERS_FILE);
    if (!is_array($users)) $users = [];
    foreach ($users as $user) {
      if (($user['group'] ?? '') === $name) {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Impossibile eliminare un gruppo assegnato a degli utenti"]);
        exit;
      }
    }
    $index = array_search($name, $groups, true);
    if ($index !== false) {
      array_splice($groups, $index, 1);
    }
    persist_groups($groups);
    echo json_encode(["success" => true]);
    break;

  default:
    http_response_code(405);
    echo json_encode(["success" => false, "message" => "Metodo non supportato"]);
}
