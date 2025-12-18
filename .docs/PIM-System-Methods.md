# Основные методы для работы в PIM системе

## 1. Авторизация и получение токена доступа

### Описание
Процесс получения токена доступа для авторизации всех последующих запросов к API PIM системы.

### Параметры токена
- **Тип запроса:** `POST`
- **Endpoint:** `/api/v1/sign-in/`
- **Срок действия:** 1 час
- **Формат авторизации:** Bearer Token

### Пример запроса

```json
{
  "login": "user_1",
  "password": "goodDay-1",
  "remember": true
}
```

### Пример ответа

```json
{
  "access": {
    "token": "eybGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X21hbmFnZXIzIiwidXNyIjoiOTY0NzZWJlM2E2OTU1YTA3YTJmZTdOGRlMTJhOGFjNjdjNTE5MjM2NjAzN2NhJmNzJjYTBkZjkwNmEyYyIsInJvbGVzIjpbIlJPTEVfSU1RVJT05BVEUiCJST0xFX01BTkFHRIiLCJST0FX0FETUlOIiwiUk9MRV9NVJLRVRFUiIsIlJPTEVf1VQRVJfQURNS4XSwiaWF0IjoxNzY0ODY2MTcwLCJleHAiOjE3NQ4Njk3NzB9.OKKrObdWRRsx-QMzBPNmgAf9_JC5TRbxYEp6_3uwwhI"
  },
  "info": null
}
```

### Использование токена
Все последующие запросы должны содержать заголовок:
```
Authorization: Bearer [полученный_токен]
```

---

## 2. Работа с каталогом

### 2.1 Создание нового каталога

**Метод:** `POST /api/v1/catalog/rapid`

#### Параметры запроса

| Параметр | Тип | Обязательный | Описание |
|----------|-----|-------------|---------|
| `id` | Integer | Нет | Идентификационный номер категории в ПИМ |
| `parentId` | Integer | Нет | Идентификационный номер родительской категории в ПИМ |
| `parentSyncUid` | String (UUID) | Нет | Идентификационный номер родительской категории (sync UID) |
| `iconId` | Integer | Нет | Идентификационный номер иконки категории в ПИМ |
| `pictureId` | Integer | Нет | Идентификационный номер фото категории в ПИМ |
| `header` | String | **Да** | Название категории |
| `syncUid` | String (UUID) | Нет | Идентификационный номер категории (sync UID) |
| `htHead` | String | Нет | Заголовок категории (HTML Head) |
| `htDesc` | String | Нет | Описание категории (HTML Description) |
| `htKeywords` | String | Нет | Ключевые слова категории |
| `content` | String | Нет | Контент категории |
| `enabled` | Boolean | Нет | Активность категории (по умолчанию: true) |
| `deleted` | Boolean | Нет | Признак удаления категории |
| `lft` | Integer | Нет | Левое значение для вложенных наборов |
| `rgt` | Integer | Нет | Правое значение для вложенных наборов |
| `level` | Integer | Нет | Уровень категории в каталоге |
| `lastLevel` | Boolean | Нет | Признак конечной категории каталога |
| `pos` | Integer | Нет | Позиция категории в каталоге |
| `productCount` | Integer | Нет | Количество товаров в категории |
| `productCountAdditional` | Integer | Нет | Количество дополнительных товаров |
| `productCountPim` | Integer | Нет | Количество товаров PIM в категории |
| `productCountPimAdditional` | Integer | Нет | Количество дополнительных товаров PIM |
| `createdAt` | DateTime (ISO 8601) | Нет | Дата создания категории (генерируется автоматически) |
| `updatedAt` | DateTime (ISO 8601) | Нет | Дата обновления категории (генерируется автоматически) |
| `terms` | Array | Нет | Синонимы категории |
| `picture` | Object | Нет | Фото категории |
| `icon` | Object | Нет | Иконка категории |
| `channelIDs` | Array[Integer] | Нет | Идентификационные номера каналов категории |
| `termIDs` | Array[Integer] | Нет | Идентификационные номера синонимов категории |
| `catalogTreeSynonym` | Boolean | Нет | Признак активности синонимов категории |
| `deleteIcon` | Boolean | Нет | Флаг удаления иконки |
| `deletePicture` | Boolean | Нет | Флаг удаления фото |

#### Пример запроса

```json
{
  "header": "ПАТИО",
  "parentId": 1,
  "syncUid": "1906282b-bf16-4069-b23c-c7b1300922da",
  "enabled": true,
  "deleted": false,
  "content": "",
  "level": 2,
  "pos": 1
}
```

#### Возможные ответы сервера

| Код | Описание | Структура ответа |
|-----|---------|------------------|
| 200 | Категория добавлена успешно | `{ "message": "string", "success": true, "errors": {}, "data": "string" }` |
| 400 | Bad Request (неправильный формат) | `{ "message": "string", "success": false, "errors": {}, "data": 0 }` |
| 403 | Forbidden (недостаточно прав) | `{ "message": "string", "success": false, "errors": {}, "data": "string" }` |
| 404 | Not Found (ресурс не найден) | `{ "message": "string", "success": false, "errors": {}, "data": "string" }` |
| 406 | Not Acceptable | `{ "message": "string", "success": false, "errors": {}, "data": 0 }` |
| 409 | Conflict (конфликт данных) | `{ "message": "string", "success": false, "errors": {}, "data": "string" }` |

### 2.2 Редактирование существующего каталога

**Метод:** `POST /api/v1/catalog/rapid/{id}`

где `{id}` - идентификатор категории

#### Описание
Редактирование параметров существующей категории в каталоге. Структура запроса идентична методу создания.

#### Пример запроса

```json
{
  "id": 9356,
  "header": "ПАТИО (обновленный)",
  "parentId": 1,
  "syncUid": "1906282b-bf16-4069-b23c-c7b1300922da",
  "enabled": true,
  "deleted": false,
  "htHead": "Мебель и аксессуары для открытых площадок",
  "htDesc": "Расширенное описание категории",
  "htKeywords": "патио, мебель, аксессуары",
  "content": "Полный контент страницы категории"
}
```

### 2.3 Получение информации по отдельному каталогу

**Метод:** `GET /api/v1/catalog/rapid/{id}`

где `{id}` - идентификатор категории

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 9356,
    "parentId": 1,
    "parentSyncUid": null,
    "iconId": null,
    "pictureId": null,
    "header": "ПАТИО",
    "syncUid": "1906282b-bf16-4069-b23c-c7b1300922da",
    "htHead": null,
    "htDesc": null,
    "htKeywords": null,
    "content": "",
    "enabled": false,
    "deleted": false,
    "lft": 48,
    "rgt": 61,
    "level": 2,
    "lastLevel": false,
    "pos": 1,
    "productCount": 4,
    "productCountAdditional": 0,
    "productCountPim": 4,
    "productCountPimAdditional": 0,
    "createdAt": "2024-04-18T08:58:19",
    "updatedAt": "2025-10-28T07:51:27",
    "terms": [],
    "picture": null,
    "icon": null,
    "channelIDs": [],
    "termIDs": [],
    "catalogTreeSynonym": false,
    "deleteIcon": false,
    "deletePicture": false,
    "roles": null
  }
}
```

### 2.4 Получение информации по дереву каталогов

**Метод:** `GET /api/v1/catalog/`

#### Описание
Получение полной структуры дерева категорий с вложенной структурой.

#### Пример ответа

```json
{
  "message": "Catalog list",
  "success": true,
  "errors": null,
  "data": [
    {
      "id": 9356,
      "header": "ПАТИО",
      "syncUid": "1906282b-bf16-4069-b23c-c7b1300922da",
      "parentId": 1,
      "children": [
        {
          "id": 9357,
          "header": "Ноутбуки и компьютеры",
          "syncUid": "eb3cb3f4-74dd-436b-84d0-7732a1ea28fd",
          "parentId": 9356,
          "children": [
            {
              "id": 9359,
              "header": "Ноутбуки и компьютерная техника",
              "syncUid": "8da5cca0-4d8e-4fe9-b8d5-d5c775b27b93",
              "parentId": 9357,
              "children": [
                {
                  "id": 9361,
                  "header": "Ноутбуки",
                  "syncUid": "d4259aa9-f13a-4eda-be4f-bf81fcd4ef2d",
                  "parentId": 9359,
                  "enabled": true,
                  "createdAt": "2024-04-18T09:05:29",
                  "updatedAt": "2025-10-28T07:51:27",
                  "level": 5,
                  "lastLevel": true,
                  "productCount": 3
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 3. Работа с Группами характеристик

### 3.1 Создание новой группы характеристик

**Метод:** `POST /api/v1/feature-group/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `id` | Integer | Идентификатор группы |
| `header` | String | Название группы характеристик |
| `pos` | Integer | Позиция в списке |
| `enabled` | Boolean | Активность группы |
| `isSystem` | Boolean | Системная группа |
| `deleted` | Boolean | Признак удаления |
| `createdAt` | DateTime | Дата создания |

#### Пример запроса

```json
{
  "id": 0,
  "header": "Группа тестовая-123",
  "pos": 0,
  "enabled": true,
  "isSystem": true,
  "deleted": false,
  "createdAt": null
}
```

### 3.2 Редактирование существующей группы характеристик

**Метод:** `POST /api/v1/feature-group/{id}`

где `{id}` - идентификатор группы характеристик

#### Пример запроса

```json
{
  "id": 1,
  "header": "Безопасность (обновленная)",
  "pos": 0,
  "enabled": true,
  "isSystem": false,
  "deleted": false
}
```

### 3.3 Получение информации о группе характеристик

**Метод:** `GET /api/v1/feature-group/{id}`

где `{id}` - идентификатор группы характеристик

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 1,
    "header": "Безопасность",
    "pos": 0,
    "enabled": true,
    "isSystem": false,
    "deleted": false,
    "createdAt": null
  }
}
```

---

## 4. Работа с Характеристиками

### 4.1 Получение информации по типу характеристики

**Метод:** `GET /api/v1/feature-type/{id}`

где `{id}` - идентификатор типа характеристики

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 1,
    "header": "Список",
    "code": "select",
    "enabled": true,
    "isSystem": true,
    "deleted": false,
    "createdAt": null
  }
}
```

### 4.2 Создание новой характеристики

**Метод:** `POST /api/v1/feature/rapid/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `id` | Integer | Идентификатор характеристики |
| `header` | String | Название характеристики |
| `code` | String | Код характеристики |
| `icon` | String | Иконка характеристики |
| `pos` | Integer | Позиция в списке |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |
| `featureTypeId` | Integer | ID типа характеристики |
| `featureType` | Object | Объект типа характеристики |
| `featureGroupId` | Integer | ID группы характеристик |
| `featureGroup` | Object | Объект группы характеристик |
| `channels` | Array | Массив каналов |
| `channelIds` | Array[Integer] | ID каналов |
| `units` | Array | Единицы измерения |
| `enabled` | Boolean | Активность характеристики |
| `deleted` | Boolean | Признак удаления |
| `gold` | Boolean | Премиум характеристика |
| `isFilter` | Boolean | Использование в фильтрах |
| `required` | Boolean | Обязательное поле |
| `isInteger` | Boolean | Целое число |
| `createdAt` | DateTime | Дата создания |
| `updatedAt` | DateTime | Дата обновления |
| `values` | Array | Массив значений характеристики |

#### Пример запроса

```json
{
  "id": 0,
  "header": "Кабина-12345",
  "code": null,
  "icon": null,
  "pos": 500,
  "syncUid": "87d7ebb2-bbb5-4bcb-9dda-cc6a228c00000",
  "featureTypeId": 1,
  "featureType": {
    "id": 1,
    "header": "Список"
  },
  "featureGroupId": 543,
  "featureGroup": {
    "id": 543,
    "header": "Строительная техника"
  },
  "channels": [
    {
      "id": 3,
      "header": "ОЗОН"
    }
  ],
  "channelIds": [3],
  "units": [],
  "enabled": true,
  "deleted": false,
  "gold": false,
  "isFilter": false,
  "required": false,
  "isInteger": false,
  "createdAt": "2025-12-16T10:57:02",
  "updatedAt": null,
  "values": [
    {
      "id": 164041,
      "code": null,
      "value": "Закрытая с кондиционированием",
      "pos": 0,
      "featureId": 28386
    }
  ]
}
```

### 4.3 Редактирование существующей характеристики

**Метод:** `POST /api/v1/feature/rapid/{id}`

где `{id}` - идентификатор характеристики

#### Описание
Структура запроса идентична методу создания.

### 4.4 Добавление характеристик в карточку товара

**Метод:** `POST /api/v1/product/template-feature-product-update/{id}`

где `{id}` - идентификатор товара в PIM

#### Параметры запроса

```json
{
  "33": 0,
  "11": "string"
}
```

где ключ - это идентификационный номер характеристики в шаблоне, значение - значение характеристики.

### 4.5 Типы характеристик и форматы передачи данных

#### 4.5.1 Строка (String)
Наиболее распространенный тип для текстовой информации.

**HTML подтип:**
```json
{
  "id_хар-ки_в_шаблоне": "<p>Текст</p>"
}
```

#### 4.5.2 Ссылка (Link)
Для ввода названия и URL ссылки.

**Формат:**
```json
{
  "id_хар-ки_в_шаблоне": "{\"header\":\"Название\",\"url\":\"https://example.com\"}"
}
```

#### 4.5.3 Числовые характеристики (Numeric)

**Число/Диапазон:**
```json
{
  "id_хар-ки_в_шаблоне": 123.45
}
```

**Интервал (формат число1...число2):**
```json
{
  "id_хар-ки_в_шаблоне": "10...20"
}
```

#### 4.5.4 Логические характеристики (Boolean)

**Формат:**
```json
{
  "id_хар-ки_в_шаблоне": true
}
```

Возможные значения: `true` или `false`

#### 4.5.5 Списки выбора (Selection Lists)

**Список (единственное значение):**
```json
{
  "id_хар-ки_в_шаблоне": 164041
}
```

**Множественный список (несколько значений):**
```json
{
  "id_хар-ки_в_шаблоне": [164041, 164042, 164043]
}
```

#### 4.5.6 Смарт-лист (Key-Value Pairs)

**Формат:**
```json
{
  "id_хар-ки_в_шаблоне": "[{\"key\":\"Ключ1\",\"value\":\"Значение1\"},{\"key\":\"Ключ2\",\"value\":\"Значение2\"}]"
}
```

### 4.6 Получение информации по характеристикам

**Метод получения всех характеристик:** `GET /api/v1/feature/`

**Метод получения одной характеристики:** `GET /api/v1/feature/{id}`

где `{id}` - идентификатор характеристики

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 28377,
    "syncUid": "fb854257-745a-4787-b47a-66f4e01fc72c",
    "header": "Длина рукояти",
    "code": null,
    "icon": null,
    "pos": 500,
    "featureType": {
      "id": 4,
      "header": "Число",
      "code": "range",
      "enabled": true,
      "isSystem": true,
      "deleted": false,
      "createdAt": "2021-05-12T10:47:00"
    },
    "featureGroup": {
      "id": 543,
      "header": "Строительная техника",
      "pos": null,
      "enabled": true,
      "isSystem": false,
      "deleted": false,
      "createdAt": null
    },
    "channels": [],
    "enabled": true,
    "isSystem": false,
    "deleted": false,
    "featureTypeId": 4,
    "featureGroupId": 543,
    "values": [
      {
        "id": 164074,
        "value": "2000",
        "code": null,
        "color": null,
        "pos": 500,
        "featureId": 28377,
        "enabled": true,
        "deleted": false,
        "createdAt": "2025-12-16T11:10:21",
        "hash": "08f90c1a417155361a5c4b8d297e0d78"
      }
    ],
    "units": [
      {
        "id": 813,
        "smallHeader": "мм",
        "enabled": true,
        "isSystem": false,
        "deleted": false,
        "header": "Миллиметр",
        "unitType": "NONE",
        "parentId": null,
        "createdAt": null,
        "subUnit": [],
        "syncUid": "63a2856b-78fb-4159-8d43-908bcee8ad48"
      }
    ]
  }
}
```

---

## 5. Работа с Группами шаблонов

### 5.1 Создание новой группы шаблонов

**Метод:** `POST /api/v1/template-group/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `id` | Integer | Идентификатор группы |
| `header` | String | Название группы шаблонов |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |
| `parentId` | Integer | ID родительской группы |
| `children` | Array | Дочерние группы |
| `lft` | Integer | Левое значение вложенного набора |
| `rgt` | Integer | Правое значение вложенного набора |
| `level` | Integer | Уровень в дереве |
| `lastLevel` | Boolean | Последний уровень |
| `templateCount` | Integer | Количество шаблонов |
| `tree` | Array[String] | Путь в дереве |
| `pos` | Integer | Позиция |
| `deleted` | Boolean | Признак удаления |
| `enabled` | Boolean | Активность |
| `createdAt` | DateTime | Дата создания |
| `updatedAt` | DateTime | Дата обновления |
| `isSystem` | Boolean | Системная группа |

#### Пример запроса

```json
{
  "id": 0,
  "header": "Новая группа-123",
  "syncUid": "a5457487-4d52-476a-8c33-145c03832222",
  "parentId": 1,
  "pos": null,
  "deleted": false,
  "enabled": true,
  "isSystem": false
}
```

### 5.2 Редактирование существующей группы шаблонов

**Метод:** `POST /api/v1/template-group/{id}`

где `{id}` - идентификатор группы шаблонов

#### Пример запроса

```json
{
  "id": 409,
  "header": "Прочее",
  "syncUid": "abee035a-0810-41f7-b6dc-1940ba1dc133",
  "parentId": 1,
  "children": [
    {
      "id": 416,
      "header": "Подраздел-1",
      "syncUid": "43166394-6f23-4968-b1a2-157698004a7d",
      "parentId": 409
    }
  ],
  "enabled": true,
  "deleted": false,
  "isSystem": false
}
```

### 5.3 Получение информации по группе шаблонов

**Метод:** `GET /api/v1/template-group/{id}`

где `{id}` - идентификатор группы шаблонов

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 409,
    "header": "Прочее",
    "syncUid": "abee035a-0810-41f7-b6dc-1940ba1dc133",
    "parentId": 1,
    "children": [
      {
        "id": 416,
        "header": "Подраздел-1",
        "syncUid": "43166394-6f23-4968-b1a2-157698004a7d",
        "parentId": 409,
        "level": 3,
        "lastLevel": true,
        "templateCount": 0,
        "tree": ["Прочее", "Подраздел-1"]
      }
    ],
    "level": 2,
    "lastLevel": false,
    "templateCount": 0,
    "tree": ["Прочее"],
    "enabled": true,
    "deleted": false,
    "isSystem": false,
    "createdAt": "2025-09-22T19:11:18",
    "updatedAt": "2025-12-16T11:00:38"
  }
}
```

---

## 6. Работа с Шаблонами

### 6.1 Создание нового шаблона

**Метод:** `POST /api/v1/template`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `id` | Integer | Идентификатор шаблона |
| `header` | String | Название шаблона |
| `templateGroupId` | Integer | ID группы шаблонов |
| `templateGroupTree` | Array | Путь в дереве групп |
| `featureCount` | Integer | Количество характеристик |
| `keyFeatureCount` | Integer | Количество ключевых характеристик |
| `productCount` | Integer | Количество товаров с этим шаблоном |
| `relatedEntity` | Integer | Связанная сущность |
| `comment` | String | Комментарий |
| `cases` | Object | Склонения названия |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |
| `deleted` | Boolean | Признак удаления |
| `createdAt` | DateTime | Дата создания |
| `updatedAt` | DateTime | Дата обновления |
| `groups` | Array | Массив групп характеристик в шаблоне |

#### Структура групп характеристик

```json
{
  "id": 427,
  "header": "Бытовая химия",
  "templateId": 401,
  "groupId": 434,
  "sort": 1,
  "features": [
    {
      "id": 0,
      "header": "Назначение",
      "templateId": 0,
      "groupId": 427,
      "groupHeader": "Бытовая химия",
      "featureId": 27481,
      "featureTypeId": 8,
      "featureGroupId": 434,
      "validatorId": null,
      "unitId": null,
      "unitHeader": null,
      "keyFeature": false,
      "multiple": false,
      "required": false,
      "isFilter": false,
      "isInteger": false,
      "sort": 1,
      "comment": null,
      "featureTypeCode": "string",
      "featureTypeHeader": "Строка",
      "units": [],
      "featureValues": [],
      "featureValuesState": null,
      "validator": null,
      "unitGroupId": null,
      "defaultUnitId": null,
      "dependentUnitIds": null,
      "unitGroup": null
    }
  ]
}
```

#### Пример полного запроса

```json
{
  "id": 0,
  "header": "Бытовая химия",
  "templateGroupId": 409,
  "templateGroupTree": [],
  "featureCount": 4,
  "keyFeatureCount": 0,
  "productCount": 2,
  "relatedEntity": 0,
  "comment": null,
  "cases": {
    "nominative": null,
    "genitive": null,
    "dative": null,
    "accusative": null,
    "creative": null,
    "prepositional": null,
    "nominativePlural": null,
    "genitivePlural": null,
    "dativePlural": null,
    "accusativePlural": null,
    "creativePlural": null,
    "prepositionalPlural": null
  },
  "syncUid": "b2e47fab-a436-4062-b97b-1513249f64b200123",
  "deleted": false,
  "createdAt": null,
  "updatedAt": null,
  "groups": []
}
```

### 6.2 Редактирование существующего шаблона

**Метод:** `POST /api/v1/template/{id}`

где `{id}` - идентификатор шаблона

#### Описание
Структура запроса идентична методу создания. При редактировании передаются все необходимые поля, включая ID.

### 6.3 Получение информации о шаблоне

**Метод:** `GET /api/v1/template/{id}`

где `{id}` - идентификатор шаблона

#### Пример ответа

```json
{
  "message": "List",
  "success": true,
  "errors": null,
  "data": {
    "id": 471,
    "header": "Монтажки слесарные",
    "templateGroupId": 410,
    "templateGroupTree": [],
    "featureCount": 3,
    "keyFeatureCount": 0,
    "productCount": 5,
    "relatedEntity": 0,
    "comment": null,
    "syncUid": "97bebd9b-b19a-4216-b430-824fc8a89d66",
    "enabled": true,
    "deleted": false,
    "createdAt": null,
    "updatedAt": null,
    "groups": [
      {
        "id": 533,
        "header": "Основные характеристики",
        "templateId": 471,
        "groupId": 521,
        "sort": 1,
        "features": []
      }
    ]
  }
}
```

### 6.4 Получение ограниченной информации обо всех шаблонах

**Метод:** `GET /api/v1/template/autocomplete/{limit}`

где `{limit}` - максимальное количество возвращаемых шаблонов

#### Описание
Возвращает список всех шаблонов с базовой информацией (id и header).

#### Пример ответа

```json
{
  "message": "List",
  "success": true,
  "errors": null,
  "data": [
    {
      "id": 434,
      "header": "Тестовый шаблон",
      "productCount": 0
    },
    {
      "id": 437,
      "header": "Обувь (386766)",
      "productCount": 386770
    },
    {
      "id": 481,
      "header": "Одежда (73)",
      "productCount": 73
    }
  ]
}
```

---

## 7. Работа с Товарами

### 7.1 Создание нового товара

**Метод:** `POST /api/v1/product/rapid/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `id` | Integer | Идентификатор товара |
| `header` | String | Название товара |
| `headerAuto` | String | Автоматически сгенерированное название |
| `fullHeader` | String | Полное название товара |
| `barCode` | String | Штрихкод |
| `articul` | String | Артикул товара |
| `content` | String | Краткое описание |
| `description` | String | Полное описание |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |
| `price` | Decimal | Цена товара |
| `enabled` | Boolean | Активность товара |
| `deleted` | Boolean | Признак удаления |
| `supplyTerm` | Integer | Срок поставки |
| `updatedAt` | DateTime | Дата обновления |
| `createdAt` | DateTime | Дата создания |
| `deletedAt` | DateTime | Дата удаления |
| `pos` | Integer | Позиция товара |
| `catalogId` | Integer | ID категории каталога |
| `catalogHeader` | String | Название категории |
| `manufacturerId` | Integer | ID производителя |
| `manufacturerSeriesId` | Integer | ID серии производителя |
| `featureUnionConditionId` | Integer | ID условия объединения характеристик |
| `countryId` | Integer | ID страны происхождения |
| `supplierId` | Integer | ID поставщика |
| `parentId` | Integer | ID родительского товара |
| `productClassId` | Integer | ID класса товара |
| `productStatusId` | Integer | ID статуса товара |
| `productGroupId` | Integer | ID группы товара |
| `unitId` | Integer | ID единицы измерения |
| `pictureId` | Integer | ID основной фотографии |
| `taxId` | Integer | ID налоговой ставки |
| `width` | Decimal | Ширина (см) |
| `height` | Decimal | Высота (см) |
| `length` | Decimal | Длина (см) |
| `weight` | Decimal | Вес (кг) |
| `volume` | Decimal | Объем |
| `guaranty` | Integer | Гарантия (месяцы) |
| `manufacturerSiteLink` | String | Ссылка на сайт производителя |
| `multiplicitySupplier` | Integer | Кратность поставки поставщиком |
| `multiplicityOrder` | Integer | Кратность заказа |
| `certificates` | String | Сертификаты |
| `minOrderQuantity` | Integer | Минимальное количество заказа |
| `productTags` | Array[Integer] | ID тегов товара |
| `productSystemTags` | Array[Integer] | ID системных тегов |
| `catalogs` | Array | Категории каталога |
| `terms` | Array | Синонимы товара |
| `videos` | Array | Видео товара |
| `picture` | Object | Основная фотография |
| `pictures` | Array | Галерея фотографий |
| `documents` | Array | Документы товара |
| `codes` | Array | Коды товара |
| `prices` | Array | Цены по типам |
| `remains` | Array | Остатки на складах |
| `linkedGoods` | Array | Связанные товары |
| `analogIDs` | Array[Integer] | ID аналогов |
| `relatedIDs` | Array[Integer] | ID связанных товаров |
| `linkedIDs` | Array[Integer] | ID связанных товаров |
| `templateFeatureValues` | Array | Значения характеристик шаблона |

#### Пример запроса (сокращенный вариант)

```json
{
  "id": 0,
  "header": "Монтажка слесарная 555мм",
  "barCode": null,
  "articul": "3926930009",
  "content": null,
  "description": null,
  "syncUid": "fa6985ef-41e8-485c-96e9-0d68b5f79c67",
  "price": 0,
  "enabled": true,
  "deleted": false,
  "supplyTerm": 0,
  "catalogId": 9611,
  "catalogHeader": "Монтажки слесарные (монтировки)",
  "pos": 500,
  "productTags": [],
  "catalogs": [
    {
      "id": 9611,
      "header": "Монтажки слесарные (монтировки)",
      "lastLevel": true
    }
  ]
}
```

### 7.2 Обновление параметров товара (частичное)

**Метод:** `POST /api/v1/product/{uid}/partial-update/`

где `{uid}` - уникальный идентификатор товара

#### Описание
Частичное обновление параметров из вкладки Инфо и характеристик товаров. Все поля являются необязательными.

#### Параметры запроса

| Параметр | Тип | Примечание |
|----------|-----|-----------|
| `header` | String | Название товара |
| `barCode` | String | Штрихкод |
| `articul` | String | Артикул |
| `catalogUid` | String (UUID) | Sync UID категории |
| `manufacturerUid` | String (UUID) | Sync UID производителя |
| `countryUid` | String (UUID) | Sync UID страны |
| `supplierUid` | String (UUID) | Sync UID поставщика |
| `unitUid` | String (UUID) | Sync UID единицы измерения |
| `taxUid` | String (UUID) | Sync UID налоговой ставки |
| `width` | Decimal | Ширина (см) |
| `height` | Decimal | Высота (см) |
| `length` | Decimal | Длина (см) |
| `weight` | Decimal | Вес (кг) |
| `volume` | Decimal | Объем |
| `guaranty` | Integer | Гарантия (месяцы) |
| `multiplicitySupplier` | Integer | Кратность поставки |
| `multiplicityOrder` | Integer | Кратность заказа |
| `minOrderQuantity` | Integer | Минимальный заказ |
| `productTags` | Array[String] | UIDs тегов товара |
| `catalogs` | Array | Категории (по syncUid) |
| `terms` | Array | Синонимы товара |
| `videos` | Array[String] | Коды видео |
| `picture` | String | Sync UID основной фотографии |
| `pictures` | Array[String] | Sync UIDs фотографий |
| `documents` | Array[String] | Sync UIDs документов |
| `codes` | Array | Коды товара |

#### Пример запроса

```json
{
  "header": "Монтажка слесарная 555мм (обновленная)",
  "articul": "3926930009-new",
  "catalogUid": "701cec5c-e958-4e73-8086-608f78ea2edd",
  "width": 10,
  "height": 5,
  "length": 55,
  "weight": 0.2,
  "guaranty": 12,
  "productTags": ["uid1", "uid2"],
  "catalogs": [
    {
      "syncUid": "701cec5c-e958-4e73-8086-608f78ea2edd",
      "header": "Монтажки слесарные (монтировки)"
    }
  ]
}
```

### 7.3 Обновление параметров товара (с использованием UIDs)

**Метод:** `POST /api/v1/product/rapid/uid/{uid}/with-uids/without-features`

где `{uid}` - уникальный идентификатор товара

#### Описание
Обновление параметров карточки товара (Атрибуты вкладки "Инфо") по UID, значения справочников также по их UID.

### 7.4 Обновление параметров товара (полное)

**Метод:** `POST /api/v1/product/uid/{uid}/without-features`

где `{uid}` - уникальный идентификатор товара

#### Описание
Полное обновление параметров карточки товара.

#### Форматы значений характеристик

1. **Список (единственное значение):** ID значения (число)
   ```json
   {
     "33": 164041
   }
   ```

2. **Множественный список (несколько значений):** Массив ID
   ```json
   {
     "33": [164041, 164042]
   }
   ```

3. **Строка/HTML:** Текстовое значение
   ```json
   {
     "33": "<p>Текст</p>"
   }
   ```

4. **Число:** Целое или дробное число (разделитель - точка)
   ```json
   {
     "33": 123.45
   }
   ```

5. **Логический тип:** true или false
   ```json
   {
     "33": true
   }
   ```

6. **Интервал:** Объект с min и max
   ```json
   {
     "33": {
       "min": 1,
       "max": 23
     }
   }
   ```

7. **Размеры:** Объект с width, height, depth
   ```json
   {
     "33": {
       "width": 411,
       "height": 21,
       "depth": 270
     }
   }
   ```

8. **Ссылка:** Объект с header и url
   ```json
   {
     "33": {
       "header": "Optional link header",
       "url": "https://some-link.ru"
     }
   }
   ```

### 7.5 Получение информации о товаре

**Метод:** `GET /api/v1/product/{id}`

где `{id}` - идентификатор товара

#### Пример ответа

```json
{
  "message": "Entity found",
  "success": true,
  "errors": null,
  "data": {
    "id": 839746,
    "header": "Монтажка слесарная 555мм",
    "barCode": null,
    "articul": "3926930009",
    "syncUid": "fa6985ef-41e8-485c-96e9-0d68b5f79c67",
    "price": 0.0,
    "enabled": true,
    "catalog": {
      "id": 9611,
      "header": "Монтажки слесарные (монтировки)",
      "syncUid": "701cec5c-e958-4e73-8086-608f78ea2edd",
      "enabled": true,
      "createdAt": "2025-10-20T21:13:46",
      "updatedAt": "2025-10-28T07:51:27",
      "level": 4,
      "lastLevel": true,
      "productCount": 5
    },
    "unit": null,
    "picture": null,
    "supplier": null,
    "manufacturer": null,
    "brand": null,
    "country": null,
    "productTags": [],
    "productSystemTags": [
      {
        "id": 5,
        "header": "Товар без доп.категории",
        "icon": "folder-remove-outline",
        "color": "basic",
        "enabled": true,
        "deleted": false,
        "syncUid": "product-without-additional-category"
      }
    ],
    "featureValues": [
      {
        "id": 161970,
        "value": "555",
        "feature": {
          "id": 20122,
          "header": "Минимальная длина, мм",
          "type": "Число",
          "group": ""
        },
        "featureId": 20122,
        "enabled": true,
        "deleted": false,
        "createdAt": "2025-10-20T21:19:37"
      }
    ],
    "catalogs": [],
    "terms": [
      {
        "id": 713,
        "header": "лопатка монтировочная"
      },
      {
        "id": 711,
        "header": "монтировка"
      }
    ],
    "videos": [],
    "pictures": [],
    "documents": [],
    "prices": [],
    "remains": [],
    "createdAt": "2025-10-20T21:19:37",
    "deleted": false
  }
}
```

---

## 8. Работа с Брендами

### 8.1 Создание нового бренда

**Метод:** `POST /api/v1/brand/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `enabled` | Boolean | Активность бренда |
| `content` | String | Описание/комментарий |
| `header` | String | Название бренда |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |

#### Пример запроса

```json
{
  "enabled": true,
  "content": "Описание бренда",
  "header": "Тест Бренд новый",
  "syncUid": "custom-uuid-1234"
}
```

### 8.2 Обновление существующего бренда

**Метод:** `POST /api/v1/brand/{id}`

где `{id}` - идентификатор бренда

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `header` | String | Название бренда |
| `content` | String | Описание |
| `enabled` | Boolean | Активность |
| `syncUid` | String (UUID) | Sync UID |
| `terms` | Array | Синонимы бренда |
| `deleted` | Boolean | Признак удаления |

#### Пример запроса

```json
{
  "header": "Тест Бренд",
  "content": "Обновленное описание",
  "enabled": true,
  "syncUid": "custom-uuid-1234",
  "terms": [],
  "deleted": false
}
```

---

## 9. Работа с Производителями

### 9.1 Создание нового производителя

**Метод:** `POST /api/v1/manufacturer/`

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `enabled` | Boolean | Активность производителя |
| `content` | String | Описание/комментарий |
| `header` | String | Название производителя |
| `syncUid` | String (UUID) | Уникальный идентификатор синхронизации |

#### Пример запроса

```json
{
  "enabled": true,
  "content": "Описание производителя",
  "header": "Производитель тестовый",
  "syncUid": "manufacturer-uuid-1234"
}
```

### 9.2 Обновление существующего производителя

**Метод (по ID):** `POST /api/v1/manufacturer/{id}`

где `{id}` - идентификатор производителя в ПИМ

**Метод (по UID):** `POST /api/v1/manufacturer/uid/{uid}`

где `{uid}` - единый идентификатор производителя

#### Параметры запроса

| Параметр | Тип | Описание |
|----------|-----|---------|
| `header` | String | Название производителя |
| `content` | String | Описание |
| `enabled` | Boolean | Активность |
| `syncUid` | String (UUID) | Sync UID |
| `terms` | Array | Синонимы производителя |
| `deleted` | Boolean | Признак удаления |

#### Пример запроса

```json
{
  "header": "Производитель",
  "content": "Обновленное описание",
  "enabled": true,
  "syncUid": "manufacturer-uuid-1234",
  "terms": [],
  "deleted": false
}
```

---

## Примечания по использованию API

### Общие принципы

1. **Авторизация:** Все запросы требуют передачи Bearer Token в заголовке `Authorization`
2. **Формат данных:** JSON для всех POST/PUT запросов
3. **DateTime формат:** ISO 8601 (например: `2024-09-02T15:20:21.904Z`)
4. **UUID формат:** Стандартный UUID v4 формат (например: `a5457487-4d52-476a-8c33-145c03832222`)
5. **Разделитель дробной части:** Точка (.)

### Коды ответов HTTP

- **200** - OK: Запрос успешно выполнен
- **400** - Bad Request: Неправильный формат запроса
- **403** - Forbidden: Недостаточно прав доступа
- **404** - Not Found: Ресурс не найден
- **406** - Not Acceptable: Неприемлемый формат
- **409** - Conflict: Конфликт данных (например, дублирование)

### Структура ответа

Все ответы API имеют следующую структуру:

```json
{
  "message": "Описание результата",
  "success": true,
  "errors": {
    "field_name": "Описание ошибки"
  },
  "data": {}
}
```

### Пагинация

Для методов получения списков используется параметр `limit` в URL для ограничения количества результатов.

### Фильтрация и сортировка

Специфичные методы поддерживают фильтрацию и сортировку через параметры запроса (детали в документации API).

---

## Версия документации

- **Дата:** Декабрь 2025
- **API версия:** v1
- **Базовый URL:** https://urv.compo-soft.ru
