<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$payload = json_decode(file_get_contents('php://input'), true);
$username = $payload['username'] ?? '';
$password = $payload['password'] ?? '';

$users = read_json_file(USERS_FILE) ?? [];
foreach ($users as $user) {
  if ($user['username'] === $username && $user['password'] === $password) {
    echo json_encode([
      "success" => true,
      "username" => $user['username'],
      "group" => $user['group'],
      "role" => $user['role'] ?? 'user'
    ]);
    exit;
  }
}
http_response_code(401);
echo json_encode(["success" => false, "message" => "Credenziali non valide"]);
