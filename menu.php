<?php
header('Content-Type: application/json');
require_once __DIR__ . '/utils.php';

$method = $_SERVER['REQUEST_METHOD'];
$rawPayload = null;
$payload = [];

if ($method !== 'GET') {
  $rawPayload = file_get_contents('php://input');
  $decoded = json_decode($rawPayload, true);
  if (is_array($decoded)) {
    $payload = $decoded;
  }
}

function normalize_menu_structure($menu) {
  if (!is_array($menu)) {
    $menu = [];
  }
  if (!isset($menu['drinks']) || !is_array($menu['drinks'])) {
    $menu['drinks'] = [];
  }
  if (!isset($menu['foods']) || !is_array($menu['foods'])) {
    $menu['foods'] = [];
  }
  $menu['drinks'] = array_values(array_filter(array_map('normalize_menu_item', $menu['drinks']), function ($item) {
    return $item['name'] !== '' && count($item['options']) > 0;
  }));
  $menu['foods'] = array_values(array_filter(array_map('normalize_menu_item', $menu['foods']), function ($item) {
    return $item['name'] !== '' && count($item['options']) > 0;
  }));
  return $menu;
}

function normalize_menu_item($item) {
  $name = '';
  $options = [];
  if (is_array($item)) {
    $name = trim((string)($item['name'] ?? ''));
    $optionsList = $item['options'] ?? [];
    if (is_array($optionsList)) {
      $unique = [];
      foreach ($optionsList as $option) {
        if (!is_string($option)) continue;
        $trimmed = trim($option);
        if ($trimmed === '' || in_array($trimmed, $unique, true)) continue;
        $unique[] = $trimmed;
      }
      $options = $unique;
    }
  }
  return ['name' => $name, 'options' => $options];
}

function persist_menu($menu) {
  if (!write_json_file(MENU_FILE, $menu)) {
    http_response_code(500);
    echo json_encode(["success" => false, "message" => "Impossibile salvare il menu"]);
    exit;
  }
}

function resolve_category_key($category) {
  $normalized = strtolower(trim((string)$category));
  if ($normalized === 'drinks' || $normalized === 'drink') {
    return 'drinks';
  }
  if ($normalized === 'foods' || $normalized === 'food') {
    return 'foods';
  }
  return null;
}

function get_item_index($menu, $categoryKey, $name) {
  if (!isset($menu[$categoryKey]) || !is_array($menu[$categoryKey])) {
    return -1;
  }
  for ($i = 0; $i < count($menu[$categoryKey]); $i++) {
    if (isset($menu[$categoryKey][$i]['name']) && $menu[$categoryKey][$i]['name'] === $name) {
      return $i;
    }
  }
  return -1;
}

$menu = read_json_file(MENU_FILE);
$menu = normalize_menu_structure($menu);

if ($method === 'GET') {
  echo json_encode([
    "success" => true,
    "drinks" => $menu['drinks'],
    "foods" => $menu['foods']
  ], JSON_UNESCAPED_UNICODE);
  exit;
}

$actorRole = (string)($payload['actorRole'] ?? '');
if ($actorRole !== 'admin') {
  http_response_code(403);
  echo json_encode(["success" => false, "message" => "Operazione permessa solo agli amministratori"]);
  exit;
}

switch ($method) {
  case 'POST':
    $categoryKey = resolve_category_key($payload['category'] ?? '');
    $name = trim((string)($payload['name'] ?? ''));
    $optionsPayload = $payload['options'] ?? [];
    $options = [];
    if (is_array($optionsPayload)) {
      foreach ($optionsPayload as $option) {
        if (!is_string($option)) continue;
        $trimmed = trim($option);
        if ($trimmed === '' || in_array($trimmed, $options, true)) continue;
        $options[] = $trimmed;
      }
    }

    if ($categoryKey === null) {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Categoria non valida"]);
      exit;
    }
    if ($name === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Il nome della voce è obbligatorio"]);
      exit;
    }
    if (count($options) === 0) {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Specificare almeno una variante"]);
      exit;
    }
    if (get_item_index($menu, $categoryKey, $name) !== -1) {
      http_response_code(409);
      echo json_encode(["success" => false, "message" => "Esiste già una voce con questo nome"]);
      exit;
    }
    $menu[$categoryKey][] = ['name' => $name, 'options' => $options];
    persist_menu($menu);
    echo json_encode(["success" => true]);
    break;

  case 'PUT':
    $categoryKey = resolve_category_key($payload['category'] ?? '');
    $name = trim((string)($payload['name'] ?? ''));
    $updates = is_array($payload['updates'] ?? null) ? $payload['updates'] : [];

    if ($categoryKey === null || $name === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Dati non validi per l'aggiornamento"]);
      exit;
    }

    $index = get_item_index($menu, $categoryKey, $name);
    if ($index === -1) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Voce non trovata"]);
      exit;
    }

    $current = $menu[$categoryKey][$index];
    $newName = trim((string)($updates['newName'] ?? $current['name']));
    if ($newName === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Il nome aggiornato non può essere vuoto"]);
      exit;
    }

    if ($newName !== $current['name'] && get_item_index($menu, $categoryKey, $newName) !== -1) {
      http_response_code(409);
      echo json_encode(["success" => false, "message" => "Esiste già una voce con il nuovo nome"]);
      exit;
    }

    $options = $current['options'];
    if (isset($updates['options'])) {
      $options = [];
      $incoming = $updates['options'];
      if (!is_array($incoming)) {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Formato varianti non valido"]);
        exit;
      }
      foreach ($incoming as $option) {
        if (!is_string($option)) continue;
        $trimmed = trim($option);
        if ($trimmed === '' || in_array($trimmed, $options, true)) continue;
        $options[] = $trimmed;
      }
      if (count($options) === 0) {
        http_response_code(400);
        echo json_encode(["success" => false, "message" => "Inserire almeno una variante"]);
        exit;
      }
    }

    $menu[$categoryKey][$index] = ['name' => $newName, 'options' => $options];
    persist_menu($menu);
    echo json_encode(["success" => true]);
    break;

  case 'DELETE':
    $categoryKey = resolve_category_key($payload['category'] ?? '');
    $name = trim((string)($payload['name'] ?? ''));

    if ($categoryKey === null || $name === '') {
      http_response_code(400);
      echo json_encode(["success" => false, "message" => "Dati non validi per l'eliminazione"]);
      exit;
    }

    $index = get_item_index($menu, $categoryKey, $name);
    if ($index === -1) {
      http_response_code(404);
      echo json_encode(["success" => false, "message" => "Voce non trovata"]);
      exit;
    }

    array_splice($menu[$categoryKey], $index, 1);
    persist_menu($menu);
    echo json_encode(["success" => true]);
    break;

  default:
    http_response_code(405);
    echo json_encode(["success" => false, "message" => "Metodo non supportato"]);
}
