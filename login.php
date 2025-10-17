<?php

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Credentials: true");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

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
