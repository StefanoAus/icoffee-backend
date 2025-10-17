<?php
// Basic config + CORS for dev
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Headers: Content-Type');
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

define('USERS_FILE', __DIR__ . '/users.json');
define('ORDERS_FILE', __DIR__ . '/orders.json');
define('GROUPS_FILE', __DIR__ . '/groups.json');
define('MENU_FILE', __DIR__ . '/menu.json');
define('PAYMENTS_FILE', __DIR__ . '/payments.json');

function read_json_file($path) {
  if (!file_exists($path)) return null;
  $json = file_get_contents($path);
  return json_decode($json, true);
}

function write_json_file($path, $data) {
  $fp = fopen($path, 'c+');
  if (!$fp) return false;
  flock($fp, LOCK_EX);
  ftruncate($fp, 0);
  fwrite($fp, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
  fflush($fp);
  flock($fp, LOCK_UN);
  fclose($fp);
  return true;
}
