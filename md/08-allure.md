# 08. Allure Report

> **Цель главы:** дать рабочее знание Allure для QA Auto — аннотации, шаги, attachments,
> категории, история, интеграция с CI и тест-менеджмент-системами. Без воды,
> только то что используется в продуктовых командах.

---

## Содержание

1. [Часть 1. Что такое Allure и зачем он нужен](#часть-1-что-такое-allure-и-зачем-он-нужен)
2. [Часть 2. Подключение к Maven + JUnit 5](#часть-2-подключение-к-maven--junit-5)
3. [Часть 3. Аннотации и метаданные](#часть-3-аннотации-и-метаданные)
4. [Часть 4. Шаги (steps) и attachments](#часть-4-шаги-steps-и-attachments)
5. [Часть 5. Интеграции (RestAssured, Playwright)](#часть-5-интеграции)
6. [Часть 6. История, тренды, категории](#часть-6-история-тренды-категории)
7. [Часть 7. Allure в CI/CD](#часть-7-allure-в-cicd)
8. [Часть 8. Allure TestOps — кратко](#часть-8-allure-testops--кратко)
9. [Чек-лист самопроверки](#чек-лист-самопроверки)
10. [Видеоматериалы](#видеоматериалы)

---

## Часть 1. Что такое Allure и зачем он нужен

### Q1. Что такое Allure Report

**Allure** — open-source фреймворк для генерации интерактивных отчётов о тестах. Состоит из:

- **Adapter** (allure-junit5, allure-rest-assured, ...) — записывает результаты в JSON во время тестов
- **Allure CLI / Maven plugin** — генерирует HTML-отчёт из этих JSON

```mermaid
flowchart LR
    T[Тесты] -->|@Step, @Attachment| A[Allure Adapter]
    A --> J[allure-results/<br/>*.json, *.txt, screenshots]
    J --> CLI[allure CLI<br/>generate]
    CLI --> H[HTML Report<br/>target/site/allure-maven-plugin/]
```

**Чем хорош:**
- Шаги, скриншоты, видео, request/response — всё в одном отчёте
- История прогонов, тренды, retries
- Категории дефектов (ошибки assert vs network vs timeout)
- Интеграция с Jira / TestRail / TMS
- Исторический анализ flaky-тестов

---

### Q2. Allure vs ExtentReport vs ReportPortal

| Критерий            | Allure              | ExtentReport         | ReportPortal             |
| ------------------- | ------------------- | -------------------- | ------------------------ |
| Формат              | static HTML         | static HTML          | server-based             |
| История             | да                  | базовая              | да (БД, ML-анализ)       |
| Real-time           | нет                 | нет                  | да                       |
| Интеграции          | RA, Selenium, Playwright | базовые          | RA, Selenium             |
| Стоимость           | бесплатно           | бесплатно/платно     | бесплатно (open-source)  |
| Поддержка           | активная (Qameta)   | средняя              | активная (EPAM)          |
| Распространенность РФ | **самый частый**  | редко                | средне                   |

> **В РФ Allure — стандарт де-факто** в QA Auto-проектах.

---

## Часть 2. Подключение к Maven + JUnit 5

### Q3. Минимальный pom.xml

```xml
<properties>
    <allure.version>2.27.0</allure.version>
    <aspectj.version>1.9.21</aspectj.version>
</properties>

<dependencies>
    <dependency>
        <groupId>io.qameta.allure</groupId>
        <artifactId>allure-junit5</artifactId>
        <version>${allure.version}</version>
        <scope>test</scope>
    </dependency>
</dependencies>

<build>
    <plugins>
        <!-- Surefire с подключением AspectJ для @Step -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.2.5</version>
            <configuration>
                <argLine>
                    -javaagent:"${settings.localRepository}/org/aspectj/aspectjweaver/${aspectj.version}/aspectjweaver-${aspectj.version}.jar"
                </argLine>
                <systemPropertyVariables>
                    <allure.results.directory>${project.build.directory}/allure-results</allure.results.directory>
                </systemPropertyVariables>
            </configuration>
            <dependencies>
                <dependency>
                    <groupId>org.aspectj</groupId>
                    <artifactId>aspectjweaver</artifactId>
                    <version>${aspectj.version}</version>
                </dependency>
            </dependencies>
        </plugin>

        <!-- Allure plugin для генерации отчёта -->
        <plugin>
            <groupId>io.qameta.allure</groupId>
            <artifactId>allure-maven</artifactId>
            <version>2.12.0</version>
            <configuration>
                <reportVersion>${allure.version}</reportVersion>
            </configuration>
        </plugin>
    </plugins>
</build>
```

> **Важно:** `aspectjweaver` нужен для работы аннотации `@Step`. Без него методы со `@Step` будут выполняться, но в отчёт не попадут.

---

### Q4. Команды генерации отчёта

```bash
# 1. Прогнать тесты — создаются target/allure-results/*.json
mvn test

# 2. Сгенерировать HTML
mvn allure:report
# → target/site/allure-maven-plugin/index.html

# 3. Сразу открыть в браузере (поднимает локальный сервер)
mvn allure:serve

# Если установлен CLI отдельно:
allure generate target/allure-results -o target/allure-report --clean
allure open target/allure-report
allure serve target/allure-results
```

---

### Q5. Установка Allure CLI

```bash
# macOS
brew install allure

# Linux
sudo apt-add-repository ppa:qameta/allure
sudo apt-get update
sudo apt-get install allure

# Windows
scoop install allure

# Через npm (везде)
npm install -g allure-commandline
```

Проверка:
```bash
allure --version
```

---

## Часть 3. Аннотации и метаданные

### Q6. Базовые аннотации

```java
import io.qameta.allure.*;
import org.junit.jupiter.api.Test;

@Epic("Платежи")
@Feature("Создание заказа")
@Story("Стандартный заказ — happy path")
@Owner("alex.smith")
@Severity(SeverityLevel.CRITICAL)
@Tag("smoke")
@Tag("payments")
class CreateOrderTest {

    @Test
    @DisplayName("Создаётся заказ с одной позицией и оплатой картой")
    @Description("Тест проверяет, что создание заказа возвращает 201 и правильный JSON")
    @Issue("JIRA-1234")
    @TmsLink("TMS-5678")
    @Link(name = "Документация API", url = "https://confluence.bank.ru/api/orders")
    void singleItemOrder() {
        // ...
    }
}
```

**Иерархия группировки:**
```
Epic
└── Feature
    └── Story
        └── Test
```

В отчёте можно фильтровать тесты по эпикам, фичам, историям.

---

### Q7. Severity — уровни

```java
@Severity(SeverityLevel.BLOCKER)    // фича не работает в принципе
@Severity(SeverityLevel.CRITICAL)   // критический сценарий
@Severity(SeverityLevel.NORMAL)     // обычный
@Severity(SeverityLevel.MINOR)      // не критично
@Severity(SeverityLevel.TRIVIAL)    // косметика
```

В отчёте Allure показывает распределение тестов по severity и помогает приоритезировать починку.

---

### Q8. Issue, TmsLink, Link

```java
@Issue("BUG-1234")                 // активный баг (отображается красным)
@TmsLink("TMS-5678")               // ссылка на тест-кейс в системе управления тестами
@Link(name = "Documentation", url = "https://...")
```

**Конфигурация ссылок** в `src/test/resources/allure.properties`:
```properties
allure.link.issue.pattern=https://jira.bank.ru/browse/{}
allure.link.tms.pattern=https://tms.bank.ru/case/{}
```

Тогда `@Issue("BUG-1234")` автоматически превратится в кликабельную ссылку.

---

### Q9. @Owner и @Lead

```java
@Owner("alex.smith")       // ответственный за тест
@Lead("team-lead")
```

В отчёте видно кто за что отвечает — удобно для отслеживания, кто чинит упавший тест.

---

## Часть 4. Шаги (steps) и attachments

### Q10. @Step — деление теста на читаемые шаги

```java
@Test
void createOrderEndToEnd() {
    User user = createUser("test@bank.ru");
    String token = login(user);
    String orderId = createOrder(token, BigDecimal.valueOf(100));
    assertOrderStatus(orderId, "PAID");
}

@Step("Создать пользователя {email}")
public User createUser(String email) {
    return usersApi.create(new CreateUserRequest(email));
}

@Step("Авторизоваться")
public String login(User user) {
    return authApi.login(user.email(), user.password()).accessToken();
}

@Step("Создать заказ на сумму {amount}")
public String createOrder(String token, BigDecimal amount) {
    return ordersApi.create(token, new CreateOrderRequest(amount)).id();
}

@Step("Проверить статус заказа = {expectedStatus}")
public void assertOrderStatus(String orderId, String expectedStatus) {
    Order o = ordersApi.get(orderId);
    assertThat(o.status()).isEqualTo(expectedStatus);
}
```

В отчёте каждый `@Step`-метод появляется как раскрывающийся блок с временем выполнения, аргументами и вложенными шагами.

---

### Q11. Allure.step(...) — программные шаги

Альтернатива аннотации — лямбда:

```java
@Test
void test() {
    Allure.step("Открыть страницу логина", () -> {
        page.navigate("/login");
    });

    Allure.step("Ввести логин и пароль", () -> {
        page.fill("#username", "user");
        page.fill("#password", "pass");
    });

    String result = Allure.step("Получить токен", (StepContext step) -> {
        step.parameter("user", "qa");
        return authApi.getToken();
    });
}
```

**Когда лучше `Allure.step` чем `@Step`:**
- Когда шаги создаются динамически
- Когда не хочется выносить логику в отдельный метод
- Когда нужно передать параметр шагу programmatically

---

### Q12. @Attachment — прикрепить файл/строку к отчёту

```java
@Attachment(value = "Screenshot", type = "image/png")
public byte[] takeScreenshot() {
    return page.screenshot();
}

@Attachment(value = "Server log", type = "text/plain")
public String fetchLog() {
    return logsClient.getLast(100);
}

@Attachment(value = "Order JSON", type = "application/json")
public String orderJson(Order order) {
    return new ObjectMapper().writeValueAsString(order);
}
```

**Программный API:**
```java
Allure.addAttachment("screenshot", "image/png",
    new ByteArrayInputStream(page.screenshot()), "png");

Allure.addAttachment("response.json", "application/json", responseBody);
```

---

### Q13. Скриншот при падении (Playwright + JUnit 5 Extension)

```java
public class ScreenshotOnFailureExtension implements TestWatcher {

    @Override
    public void testFailed(ExtensionContext ctx, Throwable cause) {
        Page page = (Page) ctx.getStore(Namespace.GLOBAL).get("page");
        if (page == null) return;

        byte[] png = page.screenshot();
        Allure.addAttachment(
            "Screenshot at failure",
            "image/png",
            new ByteArrayInputStream(png),
            "png"
        );

        // Видео из Playwright
        if (page.video() != null) {
            byte[] video = Files.readAllBytes(page.video().path());
            Allure.addAttachment("Video", "video/webm",
                new ByteArrayInputStream(video), "webm");
        }
    }
}

@ExtendWith(ScreenshotOnFailureExtension.class)
class LoginTest { /* ... */ }
```

---

### Q14. @Description vs @DisplayName

```java
@Test
@DisplayName("✅ Login: успешная авторизация")    // короткий заголовок
@Description("""
    Сценарий проверяет, что валидные учётные данные приводят
    к успешному редиректу на /dashboard и сохранению токена.

    Покрывает требование: PROD-123
    """)
void login() { }
```

В отчёте `@DisplayName` — заголовок, `@Description` — раскрывающаяся секция.

---

## Часть 5. Интеграции

### Q15. Allure + RestAssured

```xml
<dependency>
    <groupId>io.qameta.allure</groupId>
    <artifactId>allure-rest-assured</artifactId>
    <version>${allure.version}</version>
    <scope>test</scope>
</dependency>
```

```java
RequestSpecification spec = new RequestSpecBuilder()
    .setBaseUri("https://api.bank.ru")
    .addFilter(new AllureRestAssured())     // <- эта строка
    .build();
```

В отчёте каждый запрос будет отдельным шагом с:
- Method, URL, headers, query params, body
- Response status, headers, body
- Время выполнения

> Подробнее в главе [06. RestAssured](./06-rest-assured.md), Q26.

---

### Q16. Allure + Playwright

Готового адаптера нет, но интеграция простая через **Extensions**:

```java
public class AllurePlaywrightExtension implements
        BeforeEachCallback, AfterEachCallback, TestWatcher {

    @Override
    public void beforeEach(ExtensionContext ctx) {
        BrowserContext bctx = getCtx(ctx);
        bctx.tracing().start(new Tracing.StartOptions()
            .setScreenshots(true).setSnapshots(true));
    }

    @Override
    public void afterEach(ExtensionContext ctx) {
        BrowserContext bctx = getCtx(ctx);
        Path trace = Paths.get("target/traces/" + ctx.getDisplayName() + ".zip");
        bctx.tracing().stop(new Tracing.StopOptions().setPath(trace));
        Allure.addAttachment("Playwright Trace",
            "application/zip", Files.newInputStream(trace), "zip");
    }

    @Override
    public void testFailed(ExtensionContext ctx, Throwable cause) {
        Page page = getPage(ctx);
        Allure.addAttachment("Screenshot",
            "image/png", new ByteArrayInputStream(page.screenshot()), "png");
    }
}
```

В Allure-отчёте появится attachment trace.zip — открывается через Trace Viewer.

---

### Q17. Allure environment

`allure-results/environment.properties` — общая информация о среде прогона:

```properties
Browser=Chromium 121
OS=macOS 14.4
Java=17
Environment=stage
Build=1.5.42-RC1
Tester=alex.smith
```

В отчёте отображается на главной странице.

**Программное создание:**
```java
@BeforeAll
static void writeEnv() {
    Properties props = new Properties();
    props.setProperty("Browser", "Chromium 121");
    props.setProperty("Environment", System.getProperty("env"));
    try (var w = Files.newBufferedWriter(Paths.get("target/allure-results/environment.properties"))) {
        props.store(w, null);
    }
}
```

---

### Q18. Allure executors — связь с CI

`allure-results/executor.json`:

```json
{
  "name": "GitLab CI",
  "type": "gitlab",
  "url": "https://gitlab.bank.ru/qa/api-tests",
  "buildOrder": 4242,
  "buildName": "main #4242",
  "buildUrl": "https://gitlab.bank.ru/qa/api-tests/-/jobs/123456",
  "reportUrl": "https://allure.bank.ru/projects/api-tests/4242/",
  "reportName": "Allure Report"
}
```

Создаётся автоматически плагинами CI (Jenkins, GitLab) или скриптом в pipeline.

---

## Часть 6. История, тренды, категории

### Q19. История прогонов

`allure-results/history/` — папка с предыдущим прогоном. Если положить в неё файлы из старого `allure-report/history/`, новый отчёт покажет:

- **Trends** — графики по запускам
- **Retries** — сколько тестов падало в прошлый раз
- **Flaky** — тесты, которые падают и проходят без изменений

**Флоу:**
```bash
# Сохранить историю из предыдущего прогона
cp -r target/allure-report/history target/allure-results/history

# Сгенерировать новый отчёт
allure generate target/allure-results -o target/allure-report --clean
```

В CI обычно скачивают папку `history` из артефактов прошлого билда перед `allure generate`.

---

### Q20. Categories — классификация ошибок

`src/test/resources/categories.json`:

```json
[
  {
    "name": "Product defects",
    "matchedStatuses": ["failed"]
  },
  {
    "name": "Test defects",
    "matchedStatuses": ["broken"]
  },
  {
    "name": "Network issues",
    "matchedStatuses": ["broken"],
    "messageRegex": ".*(Connection refused|Timeout|UnknownHost).*"
  },
  {
    "name": "Outdated assertions",
    "matchedStatuses": ["failed"],
    "messageRegex": ".*expected.*but.*"
  },
  {
    "name": "API 5xx errors",
    "matchedStatuses": ["broken"],
    "traceRegex": ".*5\\d\\d.*"
  }
]
```

Поместить `categories.json` в `target/allure-results/` — в отчёте появится секция Categories с группировкой.

---

### Q21. Behaviors / Suites / Packages — представления

В Allure есть несколько группировок:

- **Suites** — по тестовым классам/пакетам
- **Behaviors** — по `@Epic`/`@Feature`/`@Story`
- **Packages** — по Java-пакетам
- **Categories** — по типам ошибок (см. Q20)

Переключаются вкладками в боковой панели.

---

## Часть 7. Allure в CI/CD

### Q22. GitLab CI пример

```yaml
stages:
  - test
  - report
  - deploy

test:
  stage: test
  image: maven:3.9-eclipse-temurin-17
  script:
    - mvn test
  artifacts:
    when: always
    paths:
      - target/allure-results
    expire_in: 30 days

report:
  stage: report
  image: frankescobar/allure-docker-service
  dependencies:
    - test
  script:
    # Скачать историю предыдущего билда
    - 'curl -k -L -o history.zip "$CI_PROJECT_URL/-/jobs/artifacts/$CI_DEFAULT_BRANCH/download?job=report" || true'
    - unzip -o history.zip -d ./old || true
    - cp -r ./old/allure-report/history target/allure-results/history || true
    # Сгенерировать новый
    - allure generate target/allure-results -o allure-report --clean
  artifacts:
    when: always
    paths:
      - allure-report
    expire_in: 30 days

deploy:
  stage: deploy
  script:
    - rsync -av allure-report/ user@allure-server:/var/www/allure/$CI_PROJECT_NAME/$CI_COMMIT_SHA/
  only:
    - main
```

---

### Q23. Jenkins плагин

Установить **Allure Jenkins Plugin**, в Jenkinsfile:

```groovy
post {
    always {
        allure([
            includeProperties: false,
            jdk: '',
            properties: [],
            reportBuildPolicy: 'ALWAYS',
            results: [[path: 'target/allure-results']]
        ])
    }
}
```

Плагин автоматически скачивает историю предыдущих прогонов и публикует отчёт по URL.

---

### Q24. GitHub Actions

```yaml
- name: Run tests
  run: mvn test

- name: Generate Allure report
  uses: simple-elf/allure-report-action@master
  if: always()
  with:
    allure_results: target/allure-results
    allure_history: allure-history
    keep_reports: 20

- name: Deploy report to GitHub Pages
  if: always()
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_branch: gh-pages
    publish_dir: allure-history
```

---

## Часть 8. Allure TestOps — кратко

### Q25. Allure Report vs Allure TestOps

| Критерий           | Allure Report (free)            | Allure TestOps (commercial)         |
| ------------------ | ------------------------------- | ------------------------------------ |
| Тип                | Static HTML                     | Server (Docker)                      |
| История            | На отдельных артефактах CI      | В БД, навсегда                       |
| Тест-кейсы (TMS)   | Нет                             | Полноценная TMS                      |
| Manual + Auto      | Только auto                     | Manual + Auto в одном месте          |
| Live results       | Нет                             | Real-time                            |
| Стоимость          | Free                            | Платно (есть Community-версия)       |

**В РФ-fintech часто Allure TestOps:**
- Альфа, Тинькофф, Сбер используют (или использовали)
- Решает проблему «тест-кейсы в TestRail, отчёты в Allure» — всё в одном

> На собесе достаточно знать, что **TestOps = TMS + отчёты + аналитика** в одном продукте.

---

## Чек-лист самопроверки

- [ ] Понимаю архитектуру Allure: adapter → JSON → CLI → HTML
- [ ] Подключаю allure-junit5 и allure-rest-assured к Maven
- [ ] Настраиваю aspectjweaver в Surefire
- [ ] Использую `@Epic`, `@Feature`, `@Story` для иерархии
- [ ] Применяю `@Severity` и понимаю уровни
- [ ] Конфигурирую `@Issue`/`@TmsLink` через `allure.properties`
- [ ] Пишу `@Step` с параметрами (`{paramName}`)
- [ ] Применяю `Allure.step(...)` для динамических шагов
- [ ] Прикрепляю screenshots, traces, logs через `@Attachment` или `Allure.addAttachment`
- [ ] Делаю Extension для скриншотов на падении (Playwright + Allure)
- [ ] Пишу `environment.properties` с информацией о прогоне
- [ ] Сохраняю `history/` между билдами для трендов
- [ ] Конфигурирую `categories.json` для группировки ошибок
- [ ] Настраиваю генерацию и публикацию отчёта в CI (GitLab/Jenkins/GitHub Actions)
- [ ] Знаю что такое Allure TestOps и чем отличается от report

---

## Видеоматериалы

### Русскоязычные

- **Артём Ерошенко (автор Allure) — Heisenbug доклады** — поиск на канале Heisenbug.
- **Qameta — официальный канал** — https://www.youtube.com/@qameta
- **«Allure Report для начинающих», QA Guild** — на YouTube.

### Англоязычные

- **Test Automation University — Allure** — https://testautomationu.applitools.com/allure-tutorial/
- **Allure Framework (official)** — https://github.com/allure-framework

### Документация

- **Allure Report docs** — https://allurereport.org/docs/
- **Allure JUnit 5** — https://allurereport.org/docs/junit5/
- **Allure RestAssured** — https://allurereport.org/docs/rest-assured/
- **Allure TestOps** — https://qameta.io/

---

[← Назад: 07. Spring для QA](./07-spring-for-qa.md) · [К оглавлению](./README.md) · [Следующая: 09. Архитектура автотестов →](./09-test-architecture.md)
