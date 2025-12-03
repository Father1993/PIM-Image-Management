Авторизация

POST https://demodata.compo-soft.ru/api/v1/sign-in/ - метод, который позволяет получить авторизационный токен конкретного пользователя. Этот пользователь должен существовать в системе. 
Далее, при работе с другими методами нужно скопировать токен из поля data.access.token и использовать его в поле Authorization с префиксом Bearer при каждом запросе. Срок жизни токена - один час. 
Пример запроса:

{
  "login": "login",
  "password": "password",
  "remember": true
}
Пример ответа:

{
    "message": "Tokens created",
    "success": true,
    "errors": null,
    "data": {
        "access": {
            "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X21hbmFnZXIzIiwidXNyIjoiZmRiYTNiNWJjZmQyZmU2NjNlMmI0Njg2MWMyNjJmMzdmOWY2ZmRmZWU1MmM0ODNhMGU4YjIyNDg1NGVmYjEyYSIsInJvbGVzIjpbIlJPTEVfSU1QRVJTT05BVEUiLCJST0xFX0FETUlOIiwiUk9MRV9TVVBFUl9BRE1JTiJdLCJpYXQiOjE3MTMxNjgwODEsImV4cCI6MTcxMzE3MTY4MX0.pTYU8qAHc1OdKQ9LP_6LkF_j4P88S8FxqjyMk-kK-60",
            "info": null
        }
 
Работа с Каталогом

GET https://demodata.compo-soft.ru/api/v1/catalog - метод, позволющий получить информацию о всех категориях и иерархию их вложенности (дерево категорий)

Пример ответа: 
{
    "message": "Catalog list",
    "success": true,
    "errors": null,
    "data": [
        {
            "id": 9279,
            "header": "Мастер каталог",
            "syncUid": "6c6a3d30-3ae6-42d9-b2a2-3111a9880729",
            "htHead": null,
            "htDesc": null,
            "htKeywords": null,
            "content": null,
            "parentId": 1,
            "children": [
                {
                    "id": 9320,
                    "header": "Сетевое оборудование",
                    "syncUid": "6cce9b7e-e195-453d-86fc-797293411f06",
                    "htHead": null,
                    "htDesc": null,
                    "htKeywords": null,
                    "content": "",
                    "parentId": 9279,
                    "children": [
                        {
                            "id": 9321,
                            "header": "Беспроводное оборудование",
                            "syncUid": "9a763f66-bbed-47bd-b7de-727c091b390d",
                            "htHead": null,
                            "htDesc": null,
                            "htKeywords": null,
                            "content": "",
                            "parentId": 9320,
                            "children": [],
                            "enabled": true,
                            "createdAt": "2024-02-06T17:51:33",
                            "channels": [],
                            "updatedAt": "2024-02-20T09:37:25",
                            "lft": 398,
                            "rgt": 399,
                            "level": 4,
                            "lastLevel": true,
                            "productCount": 0,
                            "productCountAdditional": 0,
                            "productCountPim": 0,
                            "productCountPimAdditional": 0,
                            "pos": 500,
                            "deleted": false,
                            "catalogTreeSynonym": false,
                            "terms": [],
                            "picture": null,
                            "icon": null,
                            "pictureInput": null,
                            "deleteIcon": false,
                            "deletePicture": false
                        }
                    ]
	    ]

GET https://demodata.compo-soft.ru/api/v1/catalog/{id} - метод, позволющий получить информацию о категории по её ID

Пример ответа: 

{
    "message": "Entity found",
    "success": true,
    "errors": null,
    "data": {
        "id": 9270,
        "header": "Обувь",
        "syncUid": "ecco-shoes",
        "htHead": null,
        "htDesc": null,
        "htKeywords": null,
        "content": null,
        "parentId": 1,
        "children": [],
        "enabled": true,
        "createdAt": "2022-09-16T15:40:40",
        "channels": [],
        "updatedAt": "2024-04-02T16:39:09",
        "lft": 406,
        "rgt": 407,
        "level": 2,
        "lastLevel": true,
        "productCount": 4,
        "productCountAdditional": 2,
        "productCountPim": 462,
        "productCountPimAdditional": 2,
        "pos": 2,
        "deleted": false,
        "catalogTreeSynonym": false,
        "terms": [
            {
                "id": 648,
                "header": "обувь для взрослых"
            }
        ],
        "picture": null,
        "icon": null,
        "pictureInput": null,
        "deleteIcon": false,
        "deletePicture": false
    }
}



POST https://demodata.compo-soft.ru/api/v1/catalog/rapid - метод, который позволяет создать новую категорию каталога. 

Пример запроса: 

{
  "id": 0,
  "parentId": 0,
  "iconId": 0,
  "pictureId": 0,
  "header": "string",
  "syncUid": "string",
  "htHead": "string",
  "htDesc": "string",
  "htKeywords": "string",
  "content": "string",
  "enabled": true,
  "deleted": true,
  "lft": 0,
  "rgt": 0,
  "level": 0,
  "lastLevel": true,
  "pos": 0,
  "productCount": 0,
  "productCountAdditional": 0,
  "productCountPim": 0,
  "productCountPimAdditional": 0,
  "createdAt": "2024-04-19T10:42:43.839Z",
  "updatedAt": "2024-04-19T10:42:43.839Z",
  "terms": [
    {
      "id": 0,
      "header": "string"
    }
  ],
  "picture": {
    "id": 0,
    "name": "string",
    "sizeX": 0,
    "sizeY": 0,
    "type": "string",
    "hash": "string",
    "deleted": true
  },
  "icon": {
    "id": 0,
    "name": "string",
    "sizeX": 0,
    "sizeY": 0,
    "type": "string",
    "hash": "string",
    "deleted": true
  },
  "channelIDs": [
    0
  ],
  "termIDs": [
    0
  ],
  "catalogTreeSynonym": true,
  "deleteIcon": true,
  "deletePicture": true
}



Ответ при созданном каталоге:

{
    "message": "Created catalog",
    "success": true,
    "errors": null,
    "data": "Created"
}

POST https://demodata.compo-soft.ru/api/v1/catalog/rapid/{id} - метод, с помощью которого осуществляется редактирование категории каталога. Каталог указывается с помощью ID 

Пример запроса:

{
  "id": 0,
  "parentId": 0,
  "iconId": 0,
  "pictureId": 0,
  "header": "string",
  "syncUid": "string",
  "htHead": "string",
  "htDesc": "string",
  "htKeywords": "string",
  "content": "string",
  "enabled": true,
  "deleted": true,
  "lft": 0,
  "rgt": 0,
  "level": 0,
  "lastLevel": true,
  "pos": 0,
  "productCount": 0,
  "productCountAdditional": 0,
  "productCountPim": 0,
  "productCountPimAdditional": 0,
  "createdAt": "2024-04-21T08:34:07.906Z",
  "updatedAt": "2024-04-21T08:34:07.906Z",
  "terms": [
    {
      "id": 0,
      "header": "string"
    }
  ],
  "picture": {
    "id": 0,
    "name": "string",
    "sizeX": 0,
    "sizeY": 0,
    "type": "string",
    "hash": "string",
    "deleted": true
  },
  "icon": {
    "id": 0,
    "name": "string",
    "sizeX": 0,
    "sizeY": 0,
    "type": "string",
    "hash": "string",
    "deleted": true
  },
  "channelIDs": [
    0
  ],
  "termIDs": [
    0
  ],
  "catalogTreeSynonym": true,
  "deleteIcon": true,
  "deletePicture": true
}

DELETE https://demodata.compo-soft.ru/api/v1/catalog/{id} - метод, который позволяет удалить категорию по её ID.

Пример ответа при удалении: 

{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}



Работа с Шаблоном

GET https://demodata.compo-soft.ru/api/v1/template/{id} - метод, позволяющий получить информацию о шаблоне и связанных с ним характеристиках по его ID. 

Пример ответа:

{
    "message": "List",
    "success": true,
    "errors": null,
    "data": {
        "id": 391,
        "header": "Коробка монтажная",
        "templateGroupId": 371,
        "templateGroupTree": [],
        "featureCount": 7,
        "keyFeatureCount": 0,
        "productCount": 1,
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
        "syncUid": "8f59b219-aac0-4535-a646-f12d41ad2975",
        "enabled": true,
        "deleted": false,
        "createdAt": null,
        "updatedAt": null,
        "groups": [
            {
                "id": 400,
                "header": "111",
                "templateId": 391,
                "groupId": 378,
                "sort": 1,
                "features": [
                    {
                        "id": 585,
                        "header": "Материал боковой стенки",
                        "templateId": 391,
                        "groupId": 400,
                        "groupHeader": "111",
                        "featureId": 24260,
                        "featureTypeId": 1,
                        "featureGroupId": 0,
                        "validatorId": null,
                        "unitId": null,
                        "unitHeader": null,
                        "keyFeature": false,
                        "multiple": false,
                        "required": true,
                        "isFilter": true,
                        "isInteger": false,
                        "sort": 1,
                        "comment": null,
                        "featureTypeCode": "select",
                        "featureTypeHeader": "Список",
                        "units": [],
                        "featureValues": [
                            121295,
                            113988,
                            122238
                        ],
                        "featureValuesState": 0,
                        "validator": null
                    },
                    {
                        "id": 586,
                        "header": "Количество встраиваемых устройств",
                        "templateId": 391,
                        "groupId": 400,
                        "groupHeader": "111",
                        "featureId": 15111,
                        "featureTypeId": 4,
                        "featureGroupId": 0,
                        "validatorId": null,
                        "unitId": null,
                        "unitHeader": null,
                        "keyFeature": false,
                        "multiple": false,
                        "required": false,
                        "isFilter": true,
                        "isInteger": false,
                        "sort": 2,
                        "comment": null,
                        "featureTypeCode": "range",
                        "featureTypeHeader": "Число",
                        "units": [],
                        "featureValues": [],
                        "featureValuesState": null,
                        "validator": null
                    },
                    {
                        "id": 591,
                        "header": "Номинальный размер",
                        "templateId": 391,
                        "groupId": 400,
                        "groupHeader": "111",
                        "featureId": 27337,
                        "featureTypeId": 8,
                        "featureGroupId": 378,
                        "validatorId": null,
                        "unitId": null,
                        "unitHeader": null,
                        "keyFeature": false,
                        "multiple": false,
                        "required": false,
                        "isFilter": false,
                        "isInteger": false,
                        "sort": 7,
                        "comment": null,
                        "featureTypeCode": "string",
                        "featureTypeHeader": "Строка",
                        "units": [],
                        "featureValues": [],
                        "featureValuesState": null,
                        "validator": null
                    }
                ]
            }
        ]
    }
}


POST https://demodata.compo-soft.ru/api/v1/template - метод, с помощью котого создается новый шаблон в системе PIM. При создании шаблона, возможно сразу добавить характеристики.

Пример запроса:

{
  "id": 0,
  "header": "string",
  "templateGroupId": 0,
  "templateGroupTree": [
    "string"
  ],
  "featureCount": 0,
  "keyFeatureCount": 0,
  "productCount": 0,
  "relatedEntity": 0,
  "comment": "string",
  "cases": {
    "nominative": "string",
    "genitive": "string",
    "dative": "string",
    "accusative": "string",
    "creative": "string",
    "prepositional": "string",
    "nominativePlural": "string",
    "genitivePlural": "string",
    "dativePlural": "string",
    "accusativePlural": "string",
    "creativePlural": "string",
    "prepositionalPlural": "string"
  },
  "syncUid": "string",
  "enabled": true,
  "deleted": true,
  "createdAt": "2024-04-25T12:50:25.669Z",
  "updatedAt": "2024-04-25T12:50:25.670Z",
  "groups": [
    {
      "id": 0,
      "header": "string",
      "templateId": 0,
      "groupId": 0,
      "sort": 0,
      "features": [
        {
          "id": 0,
          "header": "string",
          "templateId": 0,
          "groupId": 0,
          "groupHeader": "string",
          "featureId": 0,
          "featureTypeId": 0,
          "featureGroupId": 0,
          "validatorId": 0,
          "unitId": 0,
          "unitHeader": "string",
          "keyFeature": true,
          "multiple": true,
          "required": true,
          "isFilter": true,
          "isInteger": true,
          "sort": 0,
          "comment": "string",
          "featureTypeCode": "string",
          "featureTypeHeader": "string",
          "units": [
            {
              "id": 0,
              "header": "string",
              "smallHeader": "string",
              "featureId": 0
            }
          ],
          "featureValues": [
            0
          ],
          "featureValuesState": 0,
          "validator": {
            "id": 0,
            "header": "string",
            "example": "string",
            "featureTypeId": 0,
            "featureTypeHeader": "string",
            "multiple": true,
            "content": {
              "multipleSelectValidator": {
                "minValuesNumber": 0,
                "maxValuesNumber": 0
              },
              "numberValidator": {
                "minValue": 0,
                "maxValue": 0,
                "isInteger": true
              },
              "stringValidator": {
                "typeValidator": "EMAIL",
                "customValidator": {
                  "minLength": 0,
                  "maxLength": 0,
                  "useDigits": true,
                  "useCharacters": true,
                  "characters": {
                    "alphabets": [
                      "CYRILLIC"
                    ],
                    "charactersCases": [
                      "UPPERCASE"
                    ]
                  },
                  "useSymbols": true,
                  "useRegexp": true,
                  "symbols": [
                    "string"
                  ],
                  "regexp": "string"
                }
              },
              "htmlValidator": {
                "minLength": 0,
                "maxLength": 0
              },
              "intervalValidator": {
                "isInteger": true,
                "lowerBoundary": {
                  "minValue": 0,
                  "maxValue": 0
                },
                "upperBoundary": {
                  "minValue": 0,
                  "maxValue": 0
                }
              }
            },
            "deleted": true,
            "enabled": true,
            "createdAt": "2024-04-25T12:50:25.670Z",
            "updatedAt": "2024-04-25T12:50:25.670Z"
          }
        }
      ]
    }
  ],
  "relatedEntityByInt": 0
}

Ответ при созданном шаблоне: 

{
    "message": "Created",
    "success": true,
    "errors": null,
    "data": "399"
}

POST https://demodata.compo-soft.ru/api/v1/template/{id} - метод, с помощью котого осуществляется редактирование шаблона. Шаблон указывается с помощью ID 

Пример запроса:

{
  "id": 0,
  "header": "string",
  "templateGroupId": 0,
  "templateGroupTree": [
    "string"
  ],
  "featureCount": 0,
  "keyFeatureCount": 0,
  "productCount": 0,
  "relatedEntity": 0,
  "comment": "string",
  "cases": {
    "nominative": "string",
    "genitive": "string",
    "dative": "string",
    "accusative": "string",
    "creative": "string",
    "prepositional": "string",
    "nominativePlural": "string",
    "genitivePlural": "string",
    "dativePlural": "string",
    "accusativePlural": "string",
    "creativePlural": "string",
    "prepositionalPlural": "string"
  },
  "syncUid": "string",
  "enabled": true,
  "deleted": true,
  "createdAt": "2024-04-25T13:51:57.587Z",
  "updatedAt": "2024-04-25T13:51:57.587Z",
  "groups": [
    {
      "id": 0,
      "header": "string",
      "templateId": 0,
      "groupId": 0,
      "sort": 0,
      "features": [
        {
          "id": 0,
          "header": "string",
          "templateId": 0,
          "groupId": 0,
          "groupHeader": "string",
          "featureId": 0,
          "featureTypeId": 0,
          "featureGroupId": 0,
          "validatorId": 0,
          "unitId": 0,
          "unitHeader": "string",
          "keyFeature": true,
          "multiple": true,
          "required": true,
          "isFilter": true,
          "isInteger": true,
          "sort": 0,
          "comment": "string",
          "featureTypeCode": "string",
          "featureTypeHeader": "string",
          "units": [
            {
              "id": 0,
              "header": "string",
              "smallHeader": "string",
              "featureId": 0
            }
          ],
          "featureValues": [
            0
          ],
          "featureValuesState": 0,
          "validator": {
            "id": 0,
            "header": "string",
            "example": "string",
            "featureTypeId": 0,
            "featureTypeHeader": "string",
            "multiple": true,
            "content": {
              "multipleSelectValidator": {
                "minValuesNumber": 0,
                "maxValuesNumber": 0
              },
              "numberValidator": {
                "minValue": 0,
                "maxValue": 0,
                "isInteger": true
              },
              "stringValidator": {
                "typeValidator": "EMAIL",
                "customValidator": {
                  "minLength": 0,
                  "maxLength": 0,
                  "useDigits": true,
                  "useCharacters": true,
                  "characters": {
                    "alphabets": [
                      "CYRILLIC"
                    ],
                    "charactersCases": [
                      "UPPERCASE"
                    ]
                  },
                  "useSymbols": true,
                  "useRegexp": true,
                  "symbols": [
                    "string"
                  ],
                  "regexp": "string"
                }
              },
              "htmlValidator": {
                "minLength": 0,
                "maxLength": 0
              },
              "intervalValidator": {
                "isInteger": true,
                "lowerBoundary": {
                  "minValue": 0,
                  "maxValue": 0
                },
                "upperBoundary": {
                  "minValue": 0,
                  "maxValue": 0
                }
              }
            },
            "deleted": true,
            "enabled": true,
            "createdAt": "2024-04-25T13:51:57.588Z",
            "updatedAt": "2024-04-25T13:51:57.588Z"
          }
        }
      ]
    }
  ],
  "relatedEntityByInt": 0
}


DELETE https://demodata.compo-soft.ru/api/v1/template/{id} - метод, который позволяет удалить шаблон по его ID. В PIM системе реализован soft delete, котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удалении: 


{
    "message": "Template deleted",
    "success": true,
    "errors": null,
    "data": null
}

GET https://demodata.compo-soft.ru/api/v1/template-group/{id} - метод, с помощью которого можно получить информацию о группе шаблонов по её ID

Пример ответа: 


{
    "message": "Entity found",
    "success": true,
    "errors": null,
    "data": {
        "id": 374,
        "header": "Книги",
        "syncUid": "98e8bcf5-b122-43c5-8db4-83dbc6f466e9",
        "parentId": 1,
        "children": [],
        "lft": 6,
        "rgt": 7,
        "level": 2,
        "lastLevel": true,
        "templateCount": 3,
        "tree": [
            "Книги"
        ],
        "pos": null,
        "deleted": false,
        "enabled": true,
        "createdAt": "2024-04-09T10:59:47",
        "updatedAt": "2024-04-25T17:10:16",
        "isSystem": false
    }
}

POST https://demodata.compo-soft.ru/api/v1/template-group/ - метод, с помощью которого можно создать новую группу шаблонов.

Пример запроса: 


{
  "id": 0,
  "header": "string",
  "syncUid": "string",
  "parentId": 0,
  "children": [
    null
  ],
  "lft": 0,
  "rgt": 0,
  "level": 0,
  "lastLevel": true,
  "templateCount": 0,
  "tree": [
    "string"
  ],
  "pos": 0,
  "deleted": true,
  "enabled": true,
  "createdAt": "2024-04-25T14:59:29.728Z",
  "updatedAt": "2024-04-25T14:59:29.728Z",
  "isSystem": true
}

Ответ, при созданной группе:

{
    "message": "Created template group",
    "success": true,
    "errors": null,
    "data": "Created"
}

 POST https://demodata.compo-soft.ru/api/v1/template-group/{id} - метод, с помощью которого можно отредактировать группу шаблонов по её ID. 

Пример запроса:

{
  "id": 0,
  "header": "string",
  "syncUid": "string",
  "parentId": 0,
  "children": [
    null
  ],
  "lft": 0,
  "rgt": 0,
  "level": 0,
  "lastLevel": true,
  "templateCount": 0,
  "tree": [
    "string"
  ],
  "pos": 0,
  "deleted": true,
  "enabled": true,
  "createdAt": "2024-04-25T14:55:49.063Z",
  "updatedAt": "2024-04-25T14:55:49.063Z",
  "isSystem": true
}

DELETE https://demodata.compo-soft.ru/api/v1/template-group/{id} - метод, с помощью которого можно удалть группу шаблонов по её id. В PIM системе реализован soft delete, котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удалении:

{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}

Работа с Каналами


GET https://demodata.compo-soft.ru/api/v1/catalog/channels-list - метод, позволяющий получить список каналов и набор параметров каждого. 

Пример ответа:

{
    "message": "Done",
    "success": true,
    "errors": null,
    "data": [
        {
            "id": 2,
            "header": "test",
            "properties": null,
            "categories": null,
            "enabled": true,
            "isSystem": false,
            "deleted": true,
            "selectedByDefault": false,
            "createdAt": null,
           },
        {
            "id": 1,
            "header": "B2B",
            "properties": {
                "catalogId": "9270"
            },
            "categories": [],
            "enabled": true,
            "isSystem": true,
            "deleted": false,
            "selectedByDefault": false,
            "createdAt": null,
           }
     ] 
}

GET https://demodata.compo-soft.ru/api/v1/channel/{id} - метод, позволяющий получить информацию о канале по его id.

Пример ответа: 

{
    "message": "Channel found",
    "success": true,
    "errors": null,
    "data": {
        "id": 5,
        "header": "2",
        "properties": {
            "catalogId": "5482"
        },
        "categories": [],
        "enabled": true,
        "isSystem": false,
        "deleted": true,
        "selectedByDefault": false,
        "createdAt": "2022-09-07T18:10:14",
      }
}

POST https://demodata.compo-soft.ru/api/v1/channel/ - метод, с помощью которого создается новый канал с набором указанных характеристик. 

Пример запроса:
{
  "id": 0,
  "header": "string",
  "properties": {
    "additionalProp1": "string",
    "additionalProp2": "string",
    "additionalProp3": "string"
  },
  "categories": [
    {
      "id": 0,
      "header": "string",
      "children": [
        null
      ]
    }
  ],
  "enabled": true,
  "isSystem": true
 }

Пример ответа:

{
    "message": "Created",
    "success": true,
    "errors": null,
    "data": "Created"
}

POST https://demodata.compo-soft.ru/api/v1/channel/{id} - метод, позволяющий обновить информацию и характеристики канала по его id.

Пример запроса:

{
  "id": 0,
  "header": "string",
  "properties": {
    "additionalProp1": "string",
    "additionalProp2": "string",
    "additionalProp3": "string"
  },
  "categories": [
    {
      "id": 0,
      "header": "string",
      "children": [
        null
      ]
    }
  ],
  "enabled": true,
  "isSystem": true
 }

Пример ответа:

{
    "message": "Entity has been updated",
    "success": true,
    "errors": null,
    "data": "OK"
}

DELETE https://demodata.compo-soft.ru/api/v1/channel/{id} - этот метод удаляет канал по его id. В PIM системе реализован soft delete, котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удаленном канале: 
{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}

Работа с Карточкой товара 

GET https://demodata.compo-soft.ru/api/v1/product/{id} - метод, с помощью которого можно получить полную информацию и значения характеристик товара по его id


POST https://demodata.compo-soft.ru/api/v1/product/ - метод, с помощью которого можно создать новый товар в системе PIM.  

Пример запроса - пример

POST https://demodata.compo-soft.ru/api/v1/product/{id} - метод, с помощью которого можно отредактировать уже существующий товар по его id

Пример запроса - пример.

DELETE https://demodata.compo-soft.ru/api/v1/product/{id} - метод, с помощью которого можно удалить товар по его id. В PIM системе реализован soft delete, котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удаленном товаре: 

{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}

GET https://demodata.compo-soft.ru/api/v1/product/elastic/*ID каталога*/page/0/10/header/asc/?tag=*ID тега* - метод, с помощью которого можно получить список товаров и их характеристик по тегу. В запросе обязательно указывается ID Каталога и ID тега

Пример ответа:
{
    "message": "List",
    "success": true,
    "errors": null,
    "data": {
        "content": [
            {
                "id": 779289,
                "header": "(Копия)NUM (NYM)-J   4* 1,5-0,66",
                "headerAuto": null,
                "fullHeader": "(Копия)NUM (NYM)-J   4* 1,5-0,66",
                "barCode": null,
                "articul": "ELC111111111",
                "content": "",
                "description": "",
                "enabled": true,
                "syncUid": "f151a804-c1f4-11ea-aad6-005056803666",
                "pos": null,
                "productStatusId": 3,
                "featureUnionCondition": null,
                "catalogId": 5531,
                "templateId": 372,
                "templateHeader": "Ботинки для девочки",
                "catalogHeader": "NUM",
                "parentId": 0,
                "createdAt": 1638555025639,
                "updatedAt": 1709542404282,
                "catalogAdditional": [],
                "supplierId": null,
                "price": 0.0,
                "picture": null,
                "manufacturerId": 2411,
                "manufacturerHeader": "Конкорд",
                "manufacturerSeriesId": null,
                "manufacturerSeriesHeader": null,
                "productGroupId": 1482,
                "productGroupHeader": "Кабель CU до 6",
                "countryId": null,
                "countryHeader": null,
                "unit": {
                    "id": 760,
                    "smallHeader": "м",
                    "enabled": true,
                    "isSystem": false,
                    "deleted": false,
                    "header": "Метр",
                    "unitType": "BASE",
                    "parentId": 0,
                    "createdAt": null,
                    "subUnit": []
                },
                "width": 0.0,
                "height": 0.0,
                "length": 0.0,
                "weight": 0.0,
                "volume": null,
                "deleted": false,
                "features": [
                    {
                        "id": 420,
                        "header": "Объединить на одной карточке",
                        "groupId": 372,
                        "groupHeader": "Особенности",
                        "code": "3f3d348a-bda0-4f82-a3ec-b914dd69e834",
                        "type": 8,
                        "gold": false,
                        "values": [
                            {
                                "id": 152414,
                                "header": "Фамилия",
                                "value": null,
                                "intervalMin": null,
                                "intervalMax": null,
                                "width": null,
                                "height": null,
                                "depth": null
                            }
                        ]
                    },
                    {
                        "id": 541,
                        "header": "Тест строка",
                        "groupId": 372,
                        "groupHeader": "Особенности",
                        "code": "13a91be5-aed2-4fbe-ab03-0248f0a06c36",
                        "type": 8,
                        "gold": false,
                        "values": [
                            {
                                "id": 152413,
                                "header": "13",
                                "value": null,
                                "intervalMin": null,
                                "intervalMax": null,
                                "width": null,
                                "height": null,
                                "depth": null
                            }
                        ]
                    }
                ],
                "prices": null,
                "remains": [
                    {
                        "id": 962932,
                        "warehouse": {
                            "id": 69,
                            "syncUid": "e70dfffa-dddd-43ad-9554-a97309248899",
                            "header": "Поставщик",
                            "enabled": true,
                            "createdAt": "2021-12-07T06:40:46",
                            "updatedAt": "2021-12-07T06:40:46",
                            "supplierId": 1,
                            "deleted": false
                        },
                        "quantity": 0.0,
                        "availability": "NO",
                        "updatedAt": null
                    }
                ],
                "hasPrice": false,
                "recommended": null,
                "hasStock": false,
                "hasPicture": null,
                "availability": {
                    "69": "NO"
                },
                "stock": {
                    "69": 0.0
                },
                "hasInTheRegions": {
                    "22": false,
                    "23": false,
                    "24": false,
                    "25": false,
                    "26": false,
                    "49": false,
                    "27": false
                },
                "balancesOnGroupsOfWarehouses": {
                    "88": 0.0,
                    "89": 0.0,
                    "90": 0.0,
                    "91": 0.0,
                    "92": 0.0,
                    "93": 0.0,
                    "83": 0.0,
                    "94": 0.0,
                    "84": 0.0,
                    "95": 0.0,
                    "96": 0.0,
                    "85": 0.0,
                    "86": 0.0,
                    "87": 0.0
                },
                "availabilityOnGroupsOfWarehouses": {
                    "88": "NO",
                    "89": "NO",
                    "90": "NO",
                    "91": "NO",
                    "92": "NO",
                    "93": "NO",
                    "83": "NO",
                    "94": "NO",
                    "84": "NO",
                    "95": "NO",
                    "96": "NO",
                    "85": "NO",
                    "86": "NO",
                    "87": "NO"
                },
                "stockInTheRegions": {
                    "22": 0.0,
                    "23": 0.0,
                    "24": 0.0,
                    "25": 0.0,
                    "26": 0.0,
                    "49": 0.0,
                    "27": 0.0
                },
                "codes": {
                    "pc": "",
                    "raec": "",
                    "elcom": "ELC0100627012",
                    "manufacturer": "ELC111111111",
                    "etm": ""
                },
                "hasMarker": {
                    "9": true
                },
                "markers": [
                    {
                        "id": 9,
                        "header": "Хит продаж",
                        "icon": "hit",
                        "color": null,
                        "code": "0291430b-4eac-11ec-a919-005056b92142"
                    }
                ],
                "hasSystemMarker": {
                    "1": true,
                    "5": true
                },
                "systemMarkers": [
                    {
                        "id": 5,
                        "header": "Товар без доп.категории",
                        "icon": "folder-remove-outline",
                        "color": "basic",
                        "code": "product-without-additional-category"
                    },
                    {
                        "id": 1,
                        "header": "Незаполненный товар",
                        "icon": "alert-triangle-outline",
                        "color": null,
                        "code": "unfilled-product"
                    }
                ],
                "manufacturerSiteLink": "",
                "multiplicitySupplier": 0.0,
                "multiplicityOrder": 0.0,
                "minOrderQuantity": null,
                "supplyTerm": 0,
                "commercePrice": null,
                "synonyms": "",
                "synonymsCatalog": "",
                "synonymsManufacturer": "",
                "classId": null,
                "classEtimId": null,
                "className": null,
                "classSynonym": null,
                "regularAssortment": null,
                "analogCount": 1,
                "analogElasticDtos": [
                    779329
                ],
                "analogSort": [
                    {
                        "id": 779329,
                        "pos": 1000.0
                    }
                ],
                "relatedCount": 0,
                "relatedElasticDtos": null,
                "relatedSort": null,
                "nextArrival": null,
                "marketplaceChannels": null
            }


GET https://demodata.compo-soft.ru/api/v1/product/elastic/*ID каталога*/page/0/10/header/asc/?systemTag=*ID системного тега* - метод, с помощью которого можно получить список товаров и их характеристик по системному тегу. В запросе обязательно указывается ID Каталога и ID системного тега

Получение изображений товара

Для получения изображений товара необходимо выполнить запрос и получить полные данные о товаре. Запрос выполняется с помощью метода - 
GET  https://demodata.compo-soft.ru/api/v1/product/{id}
После запроса, необходимо взять данные из блока “picture” для основного фото (первое фото в карточке товара) и блока “pictures” для дополнительных фотографий
 
 
Из этих блоков берем содержимое “name” и формируем ссылку вида 
GET https://demodata.compo-soft.ru/pictures/originals/ + name + .JPG
Пример запроса:
GET  https://demodata.compo-soft.ru/pictures/originals/99/KqCx3CK5BH.JPG
В теле ответа: 


Получение ссылки на документ

Для получения прямого доступа к документов товара необходимо выполнить запрос и получить полные данные о товаре. Запрос выполняется с помощью метода - 
GET  https://demodata.compo-soft.ru/api/v1/product/{id}
После запроса, необходимо взять данные из блока “documents”
 
Из этого блока берем содержимое “fileName” и формируем ссылку вида 
GET https://demodata.compo-soft.ru/documents/ + fileName
пример запроса: https://demodata.compo-soft.ru/documents/48/2024_07_19_15311055870050_Документ Microsoft Word.pdf

В теле ответа получаем документ, который возможно сохранить на ПК, или ссылку на скачивание запрошенного документа. 
 
 


Работа с Характеристиками

GET https://demodata.compo-soft.ru/api/v1/feature/ - метод, который позволяет получить информацию по всем характеристикам в PIM.

GET https://demodata.compo-soft.ru/api/v1/feature/{id} - метод, который позволяет получить информацию о характеристике по её ID. 

Пример ответа: 

{
    "message": "Entity found",
    "success": true,
    "errors": null,
    "data": {
        "id": 27257,
        "syncUid": "326cb74a-3c3f-4865-8f51-87b5175ec481",
        "header": "Режим импорта",
        "code": null,
        "icon": null,
        "pos": 0,
        "featureType": {
            "id": 1,
            "header": "Список",
            "code": "select",
            "enabled": true,
            "isSystem": true,
            "deleted": false,
            "createdAt": null
        },
        "featureGroup": null,
        "channels": [
            {
                "id": 2,
                "header": "test",
                "properties": null,
                "categories": null,
                "enabled": true,
                "isSystem": false,
                "ozonPriceType": null,
                "ozonPriceTypeId": null,
                "ozonPremiumPriceType": null,
                "ozonPremiumPriceTypeId": null,
                "ozonMinPriceType": null,
                "ozonMinPriceTypeId": null,
                "ozonOldPriceType": null,
                "ozonOldPriceTypeId": null,
                "deleted": true,
                "selectedByDefault": false,
                "createdAt": null,
                "marketplace": null,
                "marketplaceId": null,
                "marketplaceCredential": null,
                "marketplaceCredentialId": null,
                "marketplaceCatalog": null,
                "marketplaceCatalogId": null
            }
        ],
        "catalog": [],
        "values": [
            {
                "id": 152269,
                "value": "Обновление",
                "code": null,
                "color": null,
                "pos": 1,
                "feature": {
                    "id": 27257,
                    "header": "Режим импорта",
                    "code": null,
                    "type": "Список",
                    "group": ""
                },
                "featureId": 27257,
                "enabled": true,
                "deleted": false,
                "createdAt": "2023-11-30T10:24:30",
                "pictureId": null,
                "picture": null,
                "pictureInput": null,
                "deletePicture": false,
                "description": null,
                "hash": "06f6e088f960be4833027fe082a67c81"
            },
            {
                "id": 152270,
                "value": "Создание и обновление",
                "code": null,
                "color": null,
                "pos": 2,
                "feature": {
                    "id": 27257,
                    "header": "Режим импорта",
                    "code": null,
                    "type": "Список",
                    "group": ""
                },
                "featureId": 27257,
                "enabled": true,
                "deleted": false,
                "createdAt": "2023-11-30T10:24:30",
                "pictureId": null,
                "picture": null,
                "pictureInput": null,
                "deletePicture": false,
                "description": null,
                "hash": "b2df701fd382f4d1da864fa9a101de4a"
            },
            {
                "id": 152271,
                "value": "Создание",
                "code": null,
                "color": null,
                "pos": 3,
                "feature": {
                    "id": 27257,
                    "header": "Режим импорта",
                    "code": null,
                    "type": "Список",
                    "group": ""
                },
                "featureId": 27257,
                "enabled": true,
                "deleted": false,
                "createdAt": "2023-11-30T10:24:30",
                "pictureId": null,
                "picture": null,
                "pictureInput": null,
                "deletePicture": false,
                "description": null,
                "hash": "74c7b80352f62bd4425afcf8147ec024"
            }
        ],
        "units": [],
        "featureTypeId": 1,
        "featureGroupId": null,
        "enabled": true,
        "gold": false,
        "isFilter": false,
        "required": false,
        "deleted": false,
        "isSystem": false,
        "isInteger": false,
        "sortInClass": 0,
        "createdAt": null,
        "updatedAt": "2023-11-30T10:24:10"
    }
}

POST https://demodata.compo-soft.ru/api/v1/feature/ - метод, который позволяет создать новую характеристику в системе PIM

Пример запроса: Отдельно добавить пример сразу в Gitlab

POST https://demodata.compo-soft.ru/api/v1/feature/{id} - метод, который позволяет редактировать уже существующую характеристику в системе PIM по ее id

Пример запроса: Отдельно добавить пример сразу в Gitlab

DELETE https://demodata.compo-soft.ru/api/v1/feature/{id} - метод, с помощью которого можно удалить характеристику по ее id. В PIM системе реализован soft delete, котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удаленной характеристике: 

{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}

GET https://demodata.compo-soft.ru/api/v1/feature-value/{id} - метод, который позволяет получить информацию о значении характеристики по её ID. 

Пример ответа: 

{
    "message": "Entity found",
    "success": true,
    "errors": null,
    "data": {
        "id": 152269,
        "value": "Обновление",
        "code": null,
        "color": null,
        "pos": 1,
        "feature": {
            "id": 27257,
            "header": "Режим импорта",
            "code": null,
            "type": "Список",
            "group": ""
        },
        "featureId": 27257,
        "enabled": true,
        "deleted": false,
        "createdAt": "2023-11-30T10:24:30",
        "pictureId": null,
        "picture": null,
        "pictureInput": null,
        "deletePicture": false,
        "description": null,
        "hash": "06f6e088f960be4833027fe082a67c81"
    }
}

POST https://demodata.compo-soft.ru/api/v1/feature-value/{id} - метод, который позволяет изменить значение характеристики по её ID.

Пример запроса: Отдельно добавить пример сразу в Gitlab

Работа с единицами измерения

GET https://demodata.compo-soft.ru/api/v1/unit/{id} - метод, который позволяет получить информацию о единице измерения по её ID. 

Пример ответа:

{
  "message": "string",
  "success": true,
  "errors": {
    "additionalProp1": "string",
    "additionalProp2": "string",
    "additionalProp3": "string"
  },
  "data": {
    "id": 0,
    "smallHeader": "string",
    "enabled": true,
    "isSystem": true,
    "deleted": true,
    "header": "string",
    "unitType": "NONE",
    "parentId": 0,
    "createdAt": "2024-05-02T11:23:21.170Z",
    "subUnit": [
      null
    ]
  }
}

POST https://demodata.compo-soft.ru/api/v1/unit/ - метод, который позволяет создать новую единицу измерения в системе PIM

Пример запроса: 

{
  "id": null,
  "smallHeader": "string",
  "enabled": true,
  "isSystem": true,
  "deleted": true,
  "header": "string",
  "unitType": "NONE",
  "parentId": 0,
  "createdAt": "2024-05-02T11:32:56.473Z",
  "subUnit": [
    null
  ]
}

Пример ответа при созданной единице измерения:

{
    "message": "Unit entity has been created",
    "success": true,
    "errors": null,
    "data": "788"
}

POST https://demodata.compo-soft.ru/api/v1/unit/{id} - метод, который позволяет отредактировать уже существующую единицу измерения по её id

Пример запроса: 

{
  "id": 0,
  "smallHeader": "string",
  "enabled": true,
  "isSystem": true,
  "deleted": true,
  "header": "string",
  "unitType": "NONE",
  "parentId": 0,
  "createdAt": "2024-05-02T12:54:25.508Z",
  "subUnit": [
    null
  ]
}
DELETE https://demodata.compo-soft.ru/api/v1/unit/{id} - метод, с помощью которого можно удалить единицу измерения по ее id. В PIM системе реализован soft delete, при котором сущность не удаляется, а ей присваивается тег “delete: true”. 






Пример ответа при удалении:
{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}




Группы характеристик

GET https://demodata.compo-soft.ru/api/v1/feature-group/{id} - метод, который позволяет получить информацию о группе характеристик по её id

Пример ответа:
}
   "message": "Entity found",
    "success": true,
    "errors": null,
    "data": {
        "id": 391,
        "header": "Прочие",
        "pos": 0,
        "enabled": true,
        "isSystem": false,
        "deleted": false,
        "createdAt": null
    }
}

POST https://demodata.compo-soft.ru/api/v1/feature-group/ - метод, с помощью которого создается новая группа характеристик. 

Пример запроса: 
{
  "id": 0,
  "header": "string",
  "pos": 0,
  "enabled": true,
  "isSystem": true,
  "deleted": true,
  "createdAt":null
}

Пример ответа при созданной группе: 
{
    "message": "Created",
    "success": true,
    "errors": null,
    "data": "feature-group_id"
}


POST https://demodata.compo-soft.ru/api/v1/feature-group/{id} - метод, с помощью которого редактируется группа характеристик по её id.

Пример запроса:
{
  "id": 0,
  "header": "string",
  "pos": 0,
  "enabled": true,
  "isSystem": true,
  "deleted": true,
  "createdAt":null
}

Пример ответа при верном запросе:

{
    "message": "Entity has been updated",
    "success": true,
    "errors": null,
    "data": "OK"
}

DELETE https://demodata.compo-soft.ru/api/v1/feature-group/{id} - метод, с помощью которого можно удалить группу характеристик по ее id. В PIM системе реализован soft delete, при котором сущность не удаляется, а ей присваивается тег “delete: true”. 

Пример ответа при удалении:
{
    "message": "Row deleted",
    "success": true,
    "errors": null,
    "data": null
}



Получение списка товаров без ограничения на количество записей

GET http://demodata.compo-soft.ru/api/v1/product/scroll
GET http://demodata.compo-soft.ru/api/v1/product/scroll/?scrollId={scrollId}
Где {scrollId} это ID полученный в ходе первого запроса данных состоящих из 100 документов(товаров).
Первый запрос должен идти на ендпоинт
**http://demodata.compo-soft.ru/api/v1/product/**scroll
В ответе в поле data.scrollId будет выдан scroll идентификатор, который надо подставлять во все последующие запросы.
Пример получения следующего среза данных:
**http://demodata.compo-soft.ru/api/v1/product/**scroll?scrollId=k7S0AwEOY29tcG8tcHJvZHVjdHMWZUJpblpSdkdUZWVmMTZzWTFWT1dPUQAWMzNKZ2xLUHVUYmktcFFITFdvQnBVZwAAAAAAABIJ4RY2c2pPVkpJalJaU3pQc3hKcElGSkFBAAEWZUJpblpSdkdUZWVmMTZzWTFWT1dPUQAA
Так же в качестве GET параметров можно передать:
●	manufacturerId - ID бренда;
●	catalogId - ID каталога ;
●	day - получить выборку по измененным товарам за переданное количество дней.
Пример :
GET http://demodata.compo-soft.ru/api/v1/product/scroll/0?day=1&manufacturerId=23&catalogId=919
последующие
GET http://demodata.compo-soft.ru/api/v1/product/scroll/?day=1&manufacturerId=23&catalogId=919&scrollId=k7S0AwEOY29tcG8tcHJvZHVjdHMWZUJpblpSdkdUZWVmMTZzWTFWT1dPUQAWMzNKZ2xLUHVUYmktcFFITFdvQnBVZwAAAAAAABIJ4RY2c2pPVkpJalJaU3pQc3hKcElGSkFBAAEWZUJpblpSdkdUZWVmMTZzWTFWT1dPUQAA
Так же в ответе присутствуют вспомогательные параметры, которые можно использовать в логике прокрутки товаров:
"total": 2082 - общее количество товаров в выборке.
●	Прокрутка списка заканчивается при получении нулевого количества товаров в поле data.products
●	Поле syncUId в ответе можно использовать для получения товара.



Получение информации по товару, каталогу, производителю, шаблону, характеристики по его UID 
GET 
●	/api/v1/product/uid/{uid}
●	/api/v1/product/rapid/uid/{uid}
●	/api/v1/catalog/rapid/uid/{uid}
●	/api/v1/manufacturer/uid/{uid}
●	/api/v1/template/uid/{uid}
●	/api/v1/feature/uid/{uid}
●	/api/v1/feature/rapid/uid/{uid}











