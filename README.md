###Scoring API
####Система валидации запросов к HTTP API сервиса скоринга.
***
####Cтруктура запроса:

    {"account": "<имя компании партнера>", "login": "<имя пользователя>", "method": "<имя метода>", "token":
    "<аутентификационный токен>", "arguments": {<словарь с аргументами вызываемого метода>}}

* account ‐ строка, опционально, может быть пустым
* ogin ‐ строка, обязательно, может быть пустым
* method ‐ строка, обязательно, может быть пустым
* token ‐ строка, обязательно, может быть пустым
* arguments ‐ словарь (объект в терминах json), обязательно, может быть пустым


#####Методы:

- **online_score**

    arguments:
    * phone ‐ строка или число, длиной 11, начинается с 7, опционально, может быть пустым
    * email ‐ строка, в которой есть @, опционально, может быть пустым
    * first_name ‐ строка, опционально, может быть пустым
    * last_name ‐ строка, опционально, может быть пустым
    * birthday ‐ дата в формате DD.MM. YYYY, с которой прошло не больше 70 лет, опционально, может быть пустым
    * gender ‐ число 0, 1 или 2, опционально, может быть пустым


- **clients_interests**
    
    arguments:
    * client_ids ‐ массив числе, обязательно, не пустое
    * date ‐ дата в формате DD.MM. YYYY, опционально, может быть пустым
***

####Структура ответа:

OK:

    {"code": <числовой код>, "response": {<ответ вызываемого метода>}}

Ошибка:

    {"code": <числовой код>, "error": {<сообщение об ошибке>}}
***

####Примеры запроса к API:
    $ curl -X POST -H "Content-Type: application/json" -d '{
        "account": "horns&hoofs", 
        "login": "h&f", 
        "method": "online_score", 
        "token": "55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af34e14e1d5bcd5a08f21fc95",
        "arguments": {
            "phone": "79175002040", 
            "email": "stupnikov@otus.ru", 
            "first_name": "Стансилав",
            "last_name": "Ступников", 
            "birthday": "01.01.1990", 
            "gender": 1}
    }' http://127.0.0.1:8080/method/
    
***   

    $curl -X POST -H "Content-Type: application/json" -d '{
        "account": "horns&hoofs", 
        "login": "admin", 
        "method": "clients_interests", 
        "token": "d1903948e508084abec612309cb3d9fcd11a6ca13b4ec83359001f3a57eabca8b1e5db80cd883fdc966d0bbdf23312520dcc6e3e6163ef8790e51fb7a76a0e08", 
        "arguments": {
            "client_ids": [1,2,3,4], 
            "date": "20.07.2017"
            }
    }' http://127.0.0.1:8080/method/

