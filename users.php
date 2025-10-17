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

$actorRole = 'user';
if ($method === 'GET') {
  $actorRole = $_GET['role'] ?? 'user';
} else {
  $actorRole = $payload['actorRole'] ?? 'user';
}

if ($actorRole !== 'admin') {
  http_response_code(403);
  echo json_encode(["success" => false, "message" => "Operazione permessa solo agli amministratori"]);
  exit;
}

$users = read_json_file(USERS_FILE);
if (!is_array($users)) $users = [];
$groups = read_json_file(GROUPS_FILE);
if (!is_array($groups)) $groups = [];

function group_exists($groups, $group) {
  return in_array($group, $groups, true);
}

function sanitize_role($role) {
  return $role === 'admin' ? 'admin' : 'user';
}

function persist_users($users) {
  if (!write_json_file(USERS_FILE, $users)) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Impossibile salvare gli utenti"]);
    exit;
  }
}

function count_admins($users) {
  $count = 0;
  foreach ($users as $user) {
    if (($user['role'] ?? 'user') === 'admin') {
      $count++;
    }
  }
  return $count;
}

switch ($method) {
  case 'GET':
    echo json_encode(["success" => true, "users" => $users], JSON_UNESCAPED_UNICODE);
    break;

  case 'POST':
    $newUser = $payload['user'] ?? [];
    $username = trim($newUser['username'] ?? '');
    $password = $newUser['password'] ?? '';
    $group = trim($newUser['group'] ?? '');
    $role = sanitize_role($newUser['role'] ?? 'user');

    if ($username === '' || $password === '' || $group === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Campi obbligatori mancanti"]);
      exit;
    }

    if (!group_exists($groups, $group)) {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Seleziona un gruppo valido"]);
      exit;
    }

    foreach ($users as $user) {
      if ($user['username'] === $username) {
        http_response_code(409);
        echo json_encode(["success" => false, "message" => "Username già esistente"]);
        exit;
      }
    }

    $users[] = [
      'username' => $username,
      'password' => $password,
      'group' => $group,
      'role' => $role
    ];
    persist_users($users);
    echo json_encode(["success" => true]);
    break;

  case 'PUT':
    $username = $payload['username'] ?? '';
    $updates = $payload['updates'] ?? [];

    if ($username === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Username mancante"]);
      exit;
    }

    $found = false;
    for ($i = 0; $i < count($users); $i++) {
      if ($users[$i]['username'] === $username) {
        $found = true;
        if (isset($updates['password']) && $updates['password'] !== '') {
          $users[$i]['password'] = $updates['password'];
        }
        if (isset($updates['group']) && trim($updates['group']) !== '') {
          $newGroup = trim($updates['group']);
          if (!group_exists($groups, $newGroup)) {
            http_response_code(400);
            echo json_encode(["success" => false, "message" => "Seleziona un gruppo valido"]);
            exit;
          }
          $users[$i]['group'] = $newGroup;
        }
        if (isset($updates['role'])) {
          $newRole = sanitize_role($updates['role']);
          if (($users[$i]['role'] ?? 'user') === 'admin' && $newRole !== 'admin') {
            if (count_admins($users) < 2) {
              http_response_code(400);
              echo json_encode(["success" => false, "message" => "Deve esistere almeno un amministratore"]);
              exit;
            }
          }
          $users[$i]['role'] = $newRole;
        }
        break;
      }
    }

    if (!$found) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Utente non trovato"]);
      exit;
    }

    persist_users($users);
    echo json_encode(["success" => true]);
    break;

  case 'DELETE':
    $username = $payload['username'] ?? '';
    if ($username === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Username mancante"]);
      exit;
    }

    $index = -1;
    for ($i = 0; $i < count($users); $i++) {
      if ($users[$i]['username'] === $username) {
        $index = $i;
        break;
      }
    }

    if ($index === -1) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Utente non trovato"]);
      exit;
    }

    if (($users[$index]['role'] ?? 'user') === 'admin') {
      if (count_admins($users) < 2) {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Non è possibile eliminare l'unico admin"]);
        exit;
      }
    }

    array_splice($users, $index, 1);
    persist_users($users);
    echo json_encode(["success" => true]);
    break;

  default:
    http_response_code(405);
    echo json_encode(["success" => false, "message" => "Metodo non supportato"]);
}
