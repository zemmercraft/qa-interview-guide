# 06. RestAssured (чистый синтаксис)

> **Цель главы:** дать уверенное знание чистого синтаксиса RestAssured — без обёрток
> и сгенерированных клиентов. На интервью часто просят написать запрос «с листа»,
> поэтому фокус — на DSL, спецификациях, JSON path, валидации схемы и фильтрах.

---

## Содержание

1. [Часть 1. Основы и DSL](#часть-1-основы-и-dsl)
2. [Часть 2. RequestSpecification и ResponseSpecification](#часть-2-requestspecification-и-responsespecification)
3. [Часть 3. Извлечение данных и десериализация](#часть-3-извлечение-данных-и-десериализация)
4. [Часть 4. JSON Path, XML Path, JSON Schema validation](#часть-4-json-path-xml-path-json-schema-validation)
5. [Часть 5. Авторизация](#часть-5-авторизация)
6. [Часть 6. Filters, логирование, Allure](#часть-6-filters-логирование-allure)
7. [Часть 7. Подводные камни и продвинутые темы](#часть-7-подводные-камни-и-продвинутые-темы)
8. [Чек-лист самопроверки](#чек-лист-самопроверки)
9. [Видеоматериалы](#видеоматериалы)

---

## Часть 1. Основы и DSL

### Q1. Что такое RestAssured и почему он де-факто стандарт в Java для API-тестов?

**RestAssured** — Java DSL для тестирования REST API в стиле BDD (`given()-when()-then()`).
Под капотом — Apache HttpClient, поверх — Hamcrest matchers и Groovy-подобный JSON path.

**Почему именно RestAssured:**
- Декларативный синтаксис, читается как сценарий
- Hamcrest-матчеры (`equalTo`, `hasItems`, `containsString`)
- Встроенный JSON path с фильтрами и поиском
- Сериализация/десериализация через Jackson или Gson
- Поддержка JSON Schema, OAuth, сертификатов
- Filters API для логирования, Allure, повторов

**Альтернативы:**

| Инструмент              | Когда лучше                                                |
| ----------------------- | ---------------------------------------------------------- |
| **RestAssured**         | Дефолт для UI-/API-комбинированных QA-фреймворков на Java  |
| Apache HttpClient       | Если нужен максимум контроля, перформанс                   |
| OkHttp / Retrofit       | Если уже есть production-клиент, переиспользуется в тестах |
| TestRestTemplate        | Внутри Spring Boot Test                                    |
| WebTestClient           | Реактивные/WebFlux приложения                              |
| Сгенерированные клиенты | Когда есть OpenAPI и хочется типобезопасности              |

---

### Q2. Подключение в Maven

```xml
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <version>5.4.0</version>
    <scope>test</scope>
</dependency>

<!-- JSON Schema validation -->
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>json-schema-validator</artifactId>
    <version>5.4.0</version>
    <scope>test</scope>
</dependency>

<!-- Allure integration -->
<dependency>
    <groupId>io.qameta.allure</groupId>
    <artifactId>allure-rest-assured</artifactId>
    <version>2.27.0</version>
    <scope>test</scope>
</dependency>
```

**Импорты, которые используются почти везде:**
```java
import static io.restassured.RestAssured.*;
import static io.restassured.matcher.RestAssuredMatchers.*;
import static org.hamcrest.Matchers.*;
```

---

### Q3. given() / when() / then() — что это и где разрешены вызовы?

```java
given()                                  // подготовка запроса
    .baseUri("https://api.bank.ru")
    .header("Authorization", "Bearer xxx")
    .contentType(ContentType.JSON)
    .body(payload)
.when()                                  // выполнение
    .post("/orders")
.then()                                  // валидация
    .statusCode(201)
    .body("id", notNullValue());
```

| Блок     | Что разрешено                                                         |
| -------- | --------------------------------------------------------------------- |
| `given()`| baseURI/baseUri, headers, params, queryParams, formParams, body, auth, cookies, port, contentType, multipart, redirects, log, filter, spec |
| `when()` | один из HTTP-методов: `get/post/put/patch/delete/head/options`        |
| `then()` | statusCode, headers, body (с JSON path), время отклика, schema, log   |

**Можно опускать `given()`** для простых запросов:
```java
when().get("https://api.bank.ru/orders").then().statusCode(200);
```

---

### Q4. HTTP-методы

```java
// GET
given().when().get("/users").then().statusCode(200);

// GET с path-параметром
given().pathParam("id", 42)
    .when().get("/users/{id}")
    .then().statusCode(200);

// GET с query
given().queryParam("status", "active").queryParam("limit", 10)
    .when().get("/orders")
    .then().statusCode(200);

// POST с JSON-body
given().contentType(JSON).body(Map.of("name", "Иван"))
    .when().post("/users")
    .then().statusCode(201);

// PUT
given().contentType(JSON).body(updatedUser)
    .when().put("/users/{id}", 42)
    .then().statusCode(200);

// PATCH
given().contentType(JSON).body(Map.of("email", "new@x.ru"))
    .when().patch("/users/42")
    .then().statusCode(200);

// DELETE
given().when().delete("/users/42").then().statusCode(204);
```

> Path-параметры можно передавать **через `pathParam`** или **inline** в URL: `get("/users/{id}", 42)`.

---

### Q5. Параметры разных типов: queryParam, formParam, pathParam, multiPart

```java
// query: ?status=active&limit=10
given().queryParam("status", "active").queryParam("limit", 10)
    .when().get("/orders");

// form: application/x-www-form-urlencoded
given().contentType("application/x-www-form-urlencoded")
    .formParam("username", "user").formParam("password", "pass")
    .when().post("/login");

// path: /users/42
given().pathParam("id", 42).when().get("/users/{id}");

// multipart: multipart/form-data (загрузка файла)
given()
    .multiPart("file", new File("data/passport.pdf"), "application/pdf")
    .multiPart("type", "kyc")
    .when().post("/documents");
```

`param()` — универсальный: GET → query, POST/PUT → form (если `Content-Type: application/x-www-form-urlencoded`).

---

### Q6. Body — варианты передачи

```java
// 1. String (сырой JSON)
given().contentType(JSON).body("{\"name\":\"Иван\"}")
    .when().post("/users");

// 2. Map
given().contentType(JSON).body(Map.of("name", "Иван", "age", 30))
    .when().post("/users");

// 3. POJO (Jackson сам сериализует)
record UserDto(String name, int age) {}
given().contentType(JSON).body(new UserDto("Иван", 30))
    .when().post("/users");

// 4. Файл
given().contentType(JSON).body(new File("payload.json"))
    .when().post("/users");

// 5. byte[]
given().contentType("application/octet-stream").body(byteArray)
    .when().post("/upload");
```

**Чтобы `body(POJO)` работал** — нужен Jackson или Gson в classpath. Spring Boot Starter Test уже их подтягивает.

---

### Q7. Headers и Cookies

```java
given()
    .header("X-Request-Id", UUID.randomUUID().toString())
    .header("Accept-Language", "ru-RU")
    .headers(Map.of("X-Trace", "abc", "X-User", "qa"))
    .cookie("session", "xyz")
    .cookies(Map.of("locale", "ru", "theme", "dark"))
.when().get("/profile")
.then().statusCode(200);
```

**Извлечь header / cookie из ответа:**
```java
Response r = when().get("/login");
String token = r.getHeader("Authorization");
String sid = r.getCookie("JSESSIONID");
```

---

## Часть 2. RequestSpecification и ResponseSpecification

### Q8. Зачем нужны спецификации и как их собирать?

**Проблема:** в каждом тесте повторяется `baseUri + auth + contentType + filters`.
**Решение:** один раз собрать `RequestSpecification` и переиспользовать.

```java
public class Specs {

    public static RequestSpecification authedJson(String token) {
        return new RequestSpecBuilder()
            .setBaseUri("https://api.bank.ru")
            .setContentType(ContentType.JSON)
            .setAccept(ContentType.JSON)
            .addHeader("Authorization", "Bearer " + token)
            .addFilter(new AllureRestAssured())
            .addFilter(new RequestLoggingFilter(LogDetail.URI))
            .addFilter(new ResponseLoggingFilter(LogDetail.STATUS))
            .build();
    }

    public static ResponseSpecification ok() {
        return new ResponseSpecBuilder()
            .expectStatusCode(200)
            .expectContentType(ContentType.JSON)
            .expectResponseTime(lessThan(2000L))
            .build();
    }
}
```

```java
@Test
void getUser() {
    given(Specs.authedJson(token))
        .pathParam("id", 1)
    .when()
        .get("/users/{id}")
    .then()
        .spec(Specs.ok())
        .body("id", equalTo(1));
}
```

**Глобальные дефолты** (не рекомендуется для больших проектов):
```java
RestAssured.requestSpecification = Specs.authedJson(token);
RestAssured.responseSpecification = Specs.ok();
```

---

### Q9. RequestSpecBuilder — все важные методы

```java
new RequestSpecBuilder()
    .setBaseUri("https://api.bank.ru").setBasePath("/api/v1")
    .setPort(443)
    .setContentType(ContentType.JSON)
    .setAccept("application/json")
    .addHeader("Authorization", "Bearer " + token)
    .addQueryParam("limit", 100)
    .addPathParam("env", "prod")
    .addCookie("locale", "ru")
    .setBody(payload)
    .setAuth(RestAssured.basic("user", "pass"))
    .setRelaxedHTTPSValidation()
    .addFilter(new AllureRestAssured())
    .setUrlEncodingEnabled(false)
    .build();
```

---

### Q10. ResponseSpecBuilder — что задавать

```java
new ResponseSpecBuilder()
    .expectStatusCode(200)
    .expectStatusLine(containsString("OK"))
    .expectContentType(ContentType.JSON)
    .expectHeader("Cache-Control", containsString("no-cache"))
    .expectResponseTime(lessThan(2000L))
    .expectBody("status", equalTo("OK"))
    .expectBody(matchesJsonSchemaInClasspath("schema/user.json"))
    .build();
```

---

## Часть 3. Извлечение данных и десериализация

### Q11. Способы получить данные из ответа

```java
// 1. Cохранить весь Response
Response resp = given().when().get("/users/1");
int status = resp.statusCode();
String body = resp.asString();
long timeMs = resp.time();

// 2. Извлечь в then()
Response r = given().when().get("/users/1").then().statusCode(200).extract().response();

// 3. Конкретное поле через JSON path
String name = given().when().get("/users/1").then().extract().path("name");
List<Long> ids = given().when().get("/users").then().extract().path("[*].id");

// 4. Десериализация в POJO
UserDto user = given().when().get("/users/1").then().extract().as(UserDto.class);

// 5. Десериализация коллекции
List<UserDto> users = given().when().get("/users")
    .then().extract().jsonPath().getList(".", UserDto.class);
```

---

### Q12. Десериализация в POJO

```java
public record UserDto(long id, String name, String email, Address address) {
    public record Address(String city, String street) {}
}

UserDto u = given()
    .when().get("/users/1")
    .then().statusCode(200)
    .extract().as(UserDto.class);

assertThat(u.email()).endsWith("@bank.ru");
assertThat(u.address().city()).isEqualTo("Москва");
```

**Тонкость:** имена JSON-полей должны совпадать с полями POJO либо иметь `@JsonProperty`. Для snake_case включить:

```java
ObjectMapperConfig config = ObjectMapperConfig.objectMapperConfig()
    .jackson2ObjectMapperFactory((cls, charset) ->
        new ObjectMapper().setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE));
RestAssured.config = RestAssured.config().objectMapperConfig(config);
```

---

### Q13. Получение списков и коллекций

```java
// JSON: [{"id":1,"name":"a"}, {"id":2,"name":"b"}]
List<Map<String, Object>> all = given().when().get("/users")
    .then().extract().jsonPath().getList("$");

List<UserDto> typed = given().when().get("/users")
    .then().extract().jsonPath().getList(".", UserDto.class);

// Только одно поле:
List<Long> ids = given().when().get("/users")
    .then().extract().jsonPath().getList("id", Long.class);
```

---

### Q14. Сериализация запроса с настройкой Jackson

```java
ObjectMapper jackson = new ObjectMapper()
    .registerModule(new JavaTimeModule())
    .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
    .setSerializationInclusion(JsonInclude.Include.NON_NULL);

RestAssured.config = RestAssured.config()
    .objectMapperConfig(new ObjectMapperConfig()
        .jackson2ObjectMapperFactory((cls, charset) -> jackson));
```

После этого `body(POJO)` будет сериализовать с этим mapper.

---

## Часть 4. JSON Path, XML Path, JSON Schema validation

### Q15. JSON path в RestAssured — синтаксис

JSON в примерах:
```json
{
  "user": {
    "id": 42,
    "name": "Иван",
    "roles": ["admin", "user"],
    "address": { "city": "Москва" }
  },
  "orders": [
    { "id": 1, "amount": 100, "status": "PAID" },
    { "id": 2, "amount": 200, "status": "NEW"  },
    { "id": 3, "amount": 300, "status": "PAID" }
  ]
}
```

```java
given().when().get("/me").then()
    // Простые поля
    .body("user.id",            equalTo(42))
    .body("user.name",          equalTo("Иван"))
    .body("user.address.city",  equalTo("Москва"))

    // Массивы по индексу
    .body("user.roles[0]",      equalTo("admin"))
    .body("user.roles.size()",  equalTo(2))
    .body("user.roles",         hasItem("admin"))

    // Маппинг по всем элементам
    .body("orders.id",          hasItems(1, 2, 3))
    .body("orders.status",      everyItem(in(List.of("PAID", "NEW", "CANCELLED"))))

    // Фильтрация (Groovy GPath)
    .body("orders.findAll { it.status == 'PAID' }.size()", equalTo(2))
    .body("orders.find { it.id == 2 }.amount",            equalTo(200))
    .body("orders.collect { it.amount }.sum()",            equalTo(600))
    .body("orders.max { it.amount }.id",                   equalTo(3));
```

> **Важно:** RestAssured использует **GPath** (Groovy), а не JsonPath ($.user.id). Поэтому фильтрация — через замыкания `findAll/find/collect`.

---

### Q16. JsonPath отдельно — без `then().body(...)`

```java
String json = given().when().get("/me").asString();
io.restassured.path.json.JsonPath jp = new io.restassured.path.json.JsonPath(json);

long userId = jp.getLong("user.id");
List<Integer> paidAmounts = jp.getList("orders.findAll { it.status == 'PAID' }.amount");
```

Полезно для сложного post-processing'а.

---

### Q17. XmlPath — для XML/SOAP

```java
String xml = given().when().get("/feed.xml").asString();
io.restassured.path.xml.XmlPath xp = new io.restassured.path.xml.XmlPath(xml);

String firstTitle = xp.getString("rss.channel.item[0].title");
List<String> titles = xp.getList("rss.channel.item.title");
```

В then-блоке:
```java
.body("rss.channel.item.title", hasItem("Новость дня"))
```

---

### Q18. JSON Schema validation

**Схема в `src/test/resources/schema/user.json`:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "name", "email"],
  "properties": {
    "id":    { "type": "integer" },
    "name":  { "type": "string", "minLength": 1 },
    "email": { "type": "string", "format": "email" }
  }
}
```

```java
import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchemaInClasspath;

given().when().get("/users/1")
    .then().statusCode(200)
    .body(matchesJsonSchemaInClasspath("schema/user.json"));
```

**Зачем это нужно:**
- Контракт сервиса не сломался — все обязательные поля на месте
- Типы соответствуют ожидаемым
- Проще переписывать тесты — изменилось одно поле, схема ловит

> **Best practice:** генерировать схемы из OpenAPI и держать в репозитории как часть контрактного тестирования.

---

### Q19. Hamcrest-матчеры — что нужно знать

```java
import static org.hamcrest.Matchers.*;

.body("status", equalTo("OK"))
.body("count",  greaterThan(0))
.body("count",  greaterThanOrEqualTo(10))
.body("name",   containsString("Иван"))
.body("name",   startsWith("Иван"))
.body("email",  matchesPattern(".+@bank\\.ru"))
.body("roles",  hasItem("admin"))
.body("roles",  hasItems("admin", "user"))
.body("orders", hasSize(3))
.body("city",   nullValue())
.body("city",   notNullValue())
.body("flag",   anyOf(equalTo(true), equalTo("true")))
.body("status", allOf(notNullValue(), not(equalTo("CANCELLED"))))
.body("amount", in(List.of(100, 200, 300)));
```

---

## Часть 5. Авторизация

### Q20. Bearer token

```java
given()
    .header("Authorization", "Bearer " + token)
.when().get("/me");

// Или короче
given().auth().oauth2(token).when().get("/me");
```

---

### Q21. Basic auth

```java
given().auth().basic("user", "pass").when().get("/admin");

// Preemptive — посылать заголовок сразу, не дожидаясь 401
given().auth().preemptive().basic("user", "pass").when().get("/admin");
```

---

### Q22. OAuth2 / OAuth1 / Digest

```java
given().auth().oauth2(accessToken).when().get("/api");
given().auth().digest("user", "pass").when().get("/api");
given().auth().oauth("consumerKey", "consumerSecret", "accessToken", "tokenSecret").when().get("/api");
```

---

### Q23. Получить токен и переиспользовать

```java
String token = given()
    .contentType(JSON)
    .body(Map.of("username", "qa", "password", System.getenv("QA_PASSWORD")))
.when()
    .post("https://auth.bank.ru/login")
.then()
    .statusCode(200)
    .extract().path("access_token");

RequestSpecification authedSpec = new RequestSpecBuilder()
    .setBaseUri("https://api.bank.ru")
    .addHeader("Authorization", "Bearer " + token)
    .build();

// дальше во всех тестах:
given(authedSpec).when().get("/me").then().statusCode(200);
```

---

### Q24. Клиентские сертификаты и self-signed SSL

```java
// Игнорировать self-signed сертификаты
given().relaxedHTTPSValidation().when().get("https://stage.bank.ru/api");

// Глобально:
RestAssured.useRelaxedHTTPSValidation();

// mTLS — клиентский сертификат
given().auth().certificate("/path/to/keystore.p12", "passwd",
    certAuthSettings()
        .keyStoreType("PKCS12")
        .trustStore("/path/to/truststore.jks", "trustpass"))
.when().get("https://api.bank.ru/secure");
```

---

## Часть 6. Filters, логирование, Allure

### Q25. Logging — что и когда логировать

**В тестах часто:**
```java
given().log().all()              // запрос целиком
.when().get("/users")
.then().log().ifValidationFails();  // ответ только при падении
```

**Доступные `log()` опции:**

| Метод                        | Что выводит                                         |
| ---------------------------- | --------------------------------------------------- |
| `log().all()`                | всё                                                 |
| `log().headers()`            | только заголовки                                    |
| `log().body()`               | только тело                                         |
| `log().cookies()`            | только cookies                                      |
| `log().method()`/`log().uri()` | метод и URI                                       |
| `log().ifValidationFails()`  | (only `then()`) — только если assertion упал       |
| `log().ifError()`            | только при HTTP-ошибке                              |

**Глобально через фильтры:**
```java
RestAssured.filters(new RequestLoggingFilter(), new ResponseLoggingFilter());
```

---

### Q26. Allure-фильтр

```java
// pom.xml: io.qameta.allure:allure-rest-assured

given().filter(new AllureRestAssured())
    .when().get("/users/1")
    .then().statusCode(200);
```

Каждый запрос автоматически прикладывается к Allure-отчёту: URL, headers, body, response. Шаги отображаются под `step` теста.

В `RequestSpecBuilder`:
```java
.addFilter(new AllureRestAssured())
```

---

### Q27. Кастомный Filter — общая схема

```java
public class TraceIdFilter implements Filter {
    @Override
    public Response filter(FilterableRequestSpecification req,
                           FilterableResponseSpecification resp,
                           FilterContext ctx) {
        String traceId = UUID.randomUUID().toString();
        req.header("X-Trace-Id", traceId);

        Response r = ctx.next(req, resp);

        if (r.statusCode() >= 500) {
            log.error("5xx, traceId={}, body={}", traceId, r.asString());
        }
        return r;
    }
}
```

Применение:
```java
given().filter(new TraceIdFilter()).when().get("/users");
```

---

### Q28. Замер времени и SLA-проверки

```java
given().when().get("/users/1")
    .then().time(lessThan(2000L), TimeUnit.MILLISECONDS);

// Или вручную
long ms = given().when().get("/users/1").time();
assertThat(ms).isLessThan(2000);
```

---

## Часть 7. Подводные камни и продвинутые темы

### Q29. RestAssured и `relaxedHTTPSValidation()` — когда нельзя использовать

В **проде** — никогда. Это отключает проверку сертификата. На стейдже с self-signed — допустимо, но осознанно.

---

### Q30. Тайм-ауты соединения

```java
RestAssured.config = RestAssured.config()
    .httpClient(HttpClientConfig.httpClientConfig()
        .setParam("http.connection.timeout",  5000)   // connect
        .setParam("http.socket.timeout",     30000)   // read
        .setParam("http.connection-manager.timeout", 5000L));
```

---

### Q31. Сериализация даты/времени

**Проблема:** `LocalDateTime` сериализуется как массив или ISO-строка в зависимости от настроек Jackson.

**Решение:**
```java
ObjectMapper jackson = new ObjectMapper()
    .registerModule(new JavaTimeModule())
    .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

RestAssured.config = RestAssured.config()
    .objectMapperConfig(objectMapperConfig().jackson2ObjectMapperFactory(
        (cls, charset) -> jackson));
```

Теперь `LocalDateTime` → `"2026-04-28T10:00:00"`.

---

### Q32. Параллельные тесты с RestAssured — thread-safety

`RequestSpecification`, собранный через `RequestSpecBuilder`, **immutable** и **thread-safe** при правильном использовании (без мутации после `build()`).

**Антипаттерн:** мутировать `RestAssured.requestSpecification` из разных потоков.

**Правильно:**
```java
public final class Specs {
    public static final RequestSpecification AUTHED = new RequestSpecBuilder()
        .setBaseUri("https://api.bank.ru")
        .addHeader("Authorization", "Bearer " + System.getenv("TOKEN"))
        .build();
}

// в любом тесте:
given(Specs.AUTHED).when().get("/me");
```

> Каждый `given(spec)` создаёт **новый запрос на основе спецификации** — тест не мутирует общий объект.

---

### Q33. RestAssured + Spring (если используешь Spring в фреймворке)

```java
@Configuration
public class ApiClientsConfig {

    @Bean
    public RequestSpecification authedSpec(ApiProperties props) {
        return new RequestSpecBuilder()
            .setBaseUri(props.baseUrl())
            .addHeader("Authorization", "Bearer " + props.token())
            .addFilter(new AllureRestAssured())
            .build();
    }
}

@Component
@RequiredArgsConstructor
public class OrderApiClient {
    private final RequestSpecification spec;

    public OrderDto createOrder(CreateOrderRequest body) {
        return given(spec).body(body)
            .when().post("/orders")
            .then().statusCode(201)
            .extract().as(OrderDto.class);
    }
}
```

> Подробнее в главе [07. Spring для QA](./07-spring-for-qa.md), Q35.

---

### Q34. Wrappers и сгенерированные клиенты — когда нужен RestAssured «руками»?

В fintech часто есть OpenAPI → swagger-codegen генерирует Java-клиент. Команды используют его + обёртку.

**Когда возвращаются к чистому RestAssured:**
- **Негативные кейсы**: сгенерированный клиент строго типизирован — невалидный JSON через него не отправишь.
- **Тестирование контракта** (поля «лишние», поля «пропущенные»).
- **Edge cases** с заголовками, encoding, custom Content-Type.
- **Проверка структуры ответа через JSON Schema**.
- **Когда API отдаёт нетипичный формат** (CSV, XML, бинарь).

> **На интервью:** *«Сгенерированный клиент — для счастливого пути и читаемости. Чистый RestAssured — для проверки контракта, негативки и того, что клиент скрывает (заголовки, формат body, error responses).»*

---

### Q35. Типичные ошибки на собеседовании

| Ошибка                                                      | Почему плохо                       | Как правильно                                  |
| ----------------------------------------------------------- | ---------------------------------- | ---------------------------------------------- |
| `RestAssured.baseURI = ...` глобально                       | Нечисто в parallel-тестах          | `RequestSpecBuilder.setBaseUri()`              |
| Ассертить `response.getBody().asString().contains(...)`     | Хрупко, не показывает где не нашли | `.then().body("path", containsString("..."))`  |
| Ошибаться: `body("name", equals("X"))` (Java's `equals`)    | Hamcrest требует `equalTo`         | `.body("name", equalTo("X"))`                  |
| Не закрывать ресурсы при `extract().response()`             | RestAssured всё закрывает сам      | OK как есть                                    |
| Хардкод токенов в тесте                                     | Утечка                             | env vars / Spring properties                   |
| Игнорировать `@JsonProperty` при snake_case                 | NullPointer при десериализации     | Настроить ObjectMapper или аннотации           |
| Не валидировать схему                                       | Контрактные ошибки пропускаются    | `matchesJsonSchemaInClasspath`                 |
| Печатать `System.out.println(response.asString())`           | Перегружает логи, не идёт в Allure | `log().ifValidationFails()` + AllureRestAssured |

---

## Чек-лист самопроверки

- [ ] Напишу полный CRUD-тест на чистом RestAssured за 5 минут
- [ ] Понимаю порядок `given() → when() → then()`
- [ ] Различаю `pathParam`, `queryParam`, `formParam`
- [ ] Знаю минимум 5 вариантов передать `body()`
- [ ] Собираю `RequestSpecBuilder` с filters, baseUri, auth
- [ ] Знаю минимум 10 Hamcrest матчеров
- [ ] Пишу JSON path с фильтрами `findAll`, `collect`, `max`
- [ ] Десериализую тело в POJO и `List<POJO>`
- [ ] Использую `JsonPath`/`XmlPath` отдельно
- [ ] Валидирую ответ через JSON Schema
- [ ] Подключаю `AllureRestAssured` фильтр
- [ ] Пишу свой `Filter` с trace-id
- [ ] Знаю как настроить ObjectMapper с `JavaTimeModule`
- [ ] Знаю когда использовать сгенерированный клиент, а когда чистый RestAssured
- [ ] Использую `relaxedHTTPSValidation` только осознанно

---

## Видеоматериалы

### Русскоязычные

- **Heisenbug — доклады по REST Assured** — https://www.youtube.com/@HeisenbugConf/search?query=rest+assured
- **REST Assured — практика** на канале SOWA QA, QA Guild и Артёма Русова.
- **Артём Ерошенко — Allure + RestAssured** — поиск на YouTube.

### Англоязычные

- **REST Assured (official)** — https://rest-assured.io
- **Test Automation University — REST Assured** — https://testautomationu.applitools.com/automating-your-api-tests-with-rest-assured/
- **Pavan Kumar — REST Assured** — https://www.youtube.com/playlist?list=PLhW3qG5bs-L9DloLV-PCSh1tjBJJl1nJN
- **freeCodeCamp — REST Assured** — есть полные курсы.

### Документация и статьи

- **REST Assured Usage Guide (official wiki)** — https://github.com/rest-assured/rest-assured/wiki/Usage
- **Baeldung — REST Assured** — https://www.baeldung.com/rest-assured-tutorial
- **JsonPath in REST Assured (GPath)** — https://github.com/rest-assured/rest-assured/wiki/Usage#json-using-jsonpath
- **JSON Schema** — https://json-schema.org

---

[← Назад: 05. Playwright Java](./05-playwright-java.md) · [К оглавлению](./README.md) · [Следующая: 07. Spring для QA →](./07-spring-for-qa.md)
