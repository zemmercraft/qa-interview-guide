# Глава 12. CI/CD для QA

[← Глава 11: Linux/Docker/K8s](11-linux-docker-k8s.md) | [Содержание](README.md) | [Глава 13: Алгоритмы →](13-algorithms.md)

---

## Быстрая навигация

- [Концепции CI/CD](#концепции-cicd)
- [GitLab CI](#gitlab-ci)
- [GitHub Actions](#github-actions)
- [Jenkins](#jenkins)
- [Паттерны тестирования в CI/CD](#паттерны-тестирования-в-cicd)
- [Чеклист](#чеклист)

---

## Концепции CI/CD

### Вопрос 1. Что такое CI/CD и какова роль QA в этом процессе?

```mermaid
graph LR
    DEV[Разработчик\nPush код] --> CI
    subgraph CI [Continuous Integration]
        B1[Build] --> B2[Unit Tests]
        B2 --> B3[Integration Tests]
        B3 --> B4[Code Quality]
    end
    CI --> CD
    subgraph CD [Continuous Delivery/Deployment]
        D1[Deploy Staging] --> D2[E2E Tests]
        D2 --> D3[Performance Tests]
        D3 --> D4[Deploy Production]
    end
    D4 --> MON[Monitoring\nAlerts]
    MON -->|Regression| DEV

    style CI fill:#1976D2,color:#fff
    style CD fill:#388E3C,color:#fff
```

**Роль QA в CI/CD:**

| Этап | Роль QA |
|------|---------|
| **CI: сборка** | Убедиться, что unit-тесты включены в pipeline |
| **CI: интеграционные тесты** | Настроить Testcontainers, управлять зависимостями |
| **CD: staging** | E2E-тесты против реального окружения |
| **CD: smoke** | Быстрые проверки после каждого деплоя |
| **CD: production** | Canary-тесты, мониторинг метрик |
| **Gates** | Определить критерии прохождения (pass rate, покрытие) |

**Ключевые термины:**
- **CI** (Continuous Integration) — автоматическая сборка и тестирование при каждом push
- **CD** (Continuous Delivery) — автоматическая подготовка к деплою (ручное подтверждение)
- **CD** (Continuous Deployment) — полностью автоматический деплой в prod
- **Pipeline** — набор этапов (stages) с джобами (jobs)
- **Artifact** — результат сборки: JAR, Docker-образ, Allure-отчёт
- **Gate** — условие перехода между этапами (coverage > 80%, 0 критичных ошибок)

---

### Вопрос 2. Что такое Quality Gate и как его настроить?

**Quality Gate** — набор пороговых метрик, при невыполнении которых pipeline падает.

```mermaid
graph TD
    T[Тесты выполнены] --> QG{Quality Gate}
    QG -->|Pass| NEXT[Следующий этап]
    QG -->|Fail| BLOCK[Pipeline заблокирован]

    QG --> M1[Pass rate ≥ 95%]
    QG --> M2[Coverage ≥ 80%]
    QG --> M3[Critical defects = 0]
    QG --> M4[P95 latency < 500ms]
    QG --> M5[No new high severity findings]
```

**Реализация в Maven Surefire:**
```xml
<!-- pom.xml — упасть если тестов прошло < 95% -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <!-- упасть при первом упавшем тесте в smoke -->
        <failIfNoTests>true</failIfNoTests>
    </configuration>
</plugin>

<!-- Jacoco для coverage gate -->
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <executions>
        <execution>
            <id>check</id>
            <goals><goal>check</goal></goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.80</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

---

## GitLab CI

### Вопрос 3. Как организовать `.gitlab-ci.yml` для QA-проекта?

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test-unit
  - test-integration
  - test-e2e
  - report
  - deploy

variables:
  MAVEN_OPTS: "-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository -Xmx1g"
  MAVEN_CLI_OPTS: "--batch-mode --no-transfer-progress"

# Кэш зависимостей Maven между джобами
cache:
  key: "$CI_COMMIT_REF_SLUG-maven"
  paths:
    - .m2/repository/
  policy: pull-push    # скачать в начале, залить в конце

# --- BUILD ---
build:
  stage: build
  image: maven:3.9.5-eclipse-temurin-21
  script:
    - mvn $MAVEN_CLI_OPTS compile -DskipTests
  artifacts:
    paths:
      - target/
    expire_in: 1 hour

# --- UNIT TESTS ---
unit-tests:
  stage: test-unit
  image: maven:3.9.5-eclipse-temurin-21
  script:
    - mvn $MAVEN_CLI_OPTS test -Dgroups=unit
  artifacts:
    when: always    # сохранять даже при падении
    paths:
      - target/surefire-reports/
      - target/allure-results/
    reports:
      junit: target/surefire-reports/TEST-*.xml    # GitLab встроенная интеграция

# --- INTEGRATION TESTS (с Docker-in-Docker для Testcontainers) ---
integration-tests:
  stage: test-integration
  image: maven:3.9.5-eclipse-temurin-21
  services:
    - docker:dind    # Docker-in-Docker для Testcontainers
  variables:
    DOCKER_HOST: "tcp://docker:2376"
    DOCKER_TLS_CERTDIR: "/certs"
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
  script:
    - mvn $MAVEN_CLI_OPTS test -Dgroups=integration
  artifacts:
    when: always
    paths:
      - target/allure-results/
    reports:
      junit: target/surefire-reports/TEST-*.xml

# --- E2E TESTS ---
e2e-tests:
  stage: test-e2e
  image: mcr.microsoft.com/playwright/java:v1.40.0-jammy
  variables:
    BASE_URL: $STAGING_URL
    CI: "true"
  script:
    - mvn $MAVEN_CLI_OPTS test -Dgroups=e2e -Dheadless=true
  artifacts:
    when: always
    paths:
      - target/allure-results/
      - target/playwright-traces/    # трейсы упавших тестов
    expire_in: 7 days
  only:
    - main
    - /^release\/.*/

# --- ALLURE REPORT ---
allure-report:
  stage: report
  image: frankescobar/allure-docker-service
  script:
    - allure generate target/allure-results --clean -o public/allure-report
  artifacts:
    paths:
      - public/
    expire_in: 30 days
  when: always
  pages: true    # GitLab Pages — опубликовать как сайт

# --- Параллельные тесты ---
api-tests-parallel:
  stage: test-integration
  image: maven:3.9.5-eclipse-temurin-21
  parallel: 4    # 4 параллельных job'а
  script:
    - |
      TOTAL=$CI_NODE_TOTAL
      INDEX=$CI_NODE_INDEX
      mvn test -Dgroups=api \
        -Dsurefire.forkCount=$TOTAL \
        -Dsurefire.threadCount=1 \
        -Dtest.node.index=$INDEX \
        -Dtest.node.total=$TOTAL
```

---

### Вопрос 4. Как настроить Testcontainers в GitLab CI (Docker-in-Docker)?

```yaml
# Два варианта запуска Testcontainers в GitLab CI

# Вариант 1: Docker-in-Docker (dind)
integration-dind:
  services:
    - name: docker:24-dind
      alias: docker
      command: ["--tls=false"]
  variables:
    DOCKER_HOST: "tcp://docker:2375"
    DOCKER_TLS_CERTDIR: ""
    TESTCONTAINERS_HOST_OVERRIDE: "docker"
    TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE: "/var/run/docker.sock"
  before_script:
    - apt-get install -y docker-cli    # установить docker CLI
  script:
    - mvn test -Dgroups=integration

# Вариант 2: Ryuk disabled + host Docker socket (если runner настроен)
integration-socket:
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
    TESTCONTAINERS_RYUK_DISABLED: "true"    # отключить cleanup-агент
  script:
    - mvn test -Dgroups=integration
```

**`testcontainers.properties` для CI:**
```properties
# src/test/resources/testcontainers.properties
docker.client.strategy=org.testcontainers.dockerclient.EnvironmentAndSystemPropertyClientProviderStrategy
testcontainers.reuse.enable=false    # в CI не переиспользуем
```

---

### Вопрос 5. Как настроить environments и manual approval в GitLab CI?

```yaml
# Окружения и ручное подтверждение
deploy-staging:
  stage: deploy
  script:
    - helm upgrade --install myapp ./charts/myapp --set image.tag=$CI_COMMIT_SHA -n staging
  environment:
    name: staging
    url: https://staging.example.com
  only:
    - main

smoke-staging:
  stage: test-e2e
  script:
    - mvn test -Dgroups=smoke -Dbase.url=https://staging.example.com
  environment:
    name: staging
  needs: [deploy-staging]    # запустить после deploy-staging

deploy-production:
  stage: deploy
  script:
    - helm upgrade --install myapp ./charts/myapp --set image.tag=$CI_COMMIT_SHA -n production
  environment:
    name: production
    url: https://example.com
  when: manual          # ручное подтверждение!
  allow_failure: false
  needs: [smoke-staging]
  only:
    - main
```

---

## GitHub Actions

### Вопрос 6. Как организовать тесты в GitHub Actions?

```yaml
# .github/workflows/tests.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'    # каждую ночь в 02:00

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Java 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'    # кэш Maven зависимостей

      - name: Run unit tests
        run: mvn test -Dgroups=unit --no-transfer-progress

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()    # загружать даже при падении
        with:
          name: unit-test-results
          path: target/surefire-reports/

      - name: Publish test report
        uses: dorny/test-reporter@v1
        if: always()
        with:
          name: Unit Tests
          path: 'target/surefire-reports/TEST-*.xml'
          reporter: java-junit

  integration-tests:
    runs-on: ubuntu-latest
    # Docker доступен на ubuntu-latest — Testcontainers работает из коробки!
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'

      - name: Run integration tests
        run: mvn test -Dgroups=integration --no-transfer-progress

      - name: Upload Allure results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: allure-results
          path: target/allure-results/

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]    # только если предыдущие прошли
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: 'maven'

      - name: Install Playwright browsers
        run: mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps chromium"

      - name: Run E2E tests
        run: mvn test -Dgroups=e2e
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}
          CI: true

      - name: Upload Playwright traces
        uses: actions/upload-artifact@v4
        if: failure()    # только при падении
        with:
          name: playwright-traces
          path: target/playwright-traces/

  allure-report:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests]
    if: always()
    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          pattern: allure-results*
          merge-multiple: true
          path: allure-results/

      - name: Generate Allure report
        uses: simple-elf/allure-report-action@master
        with:
          allure_results: allure-results
          gh_pages: gh-pages
          allure_history: allure-history

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./allure-history
```

---

### Вопрос 7. Как параллельно запускать тесты в GitHub Actions?

```yaml
# Параллельная матрица тестов
e2e-parallel:
  runs-on: ubuntu-latest
  strategy:
    fail-fast: false    # не останавливать остальные при падении одного
    matrix:
      shard: [1, 2, 3, 4]    # 4 параллельных runner'а
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-java@v4
      with:
        java-version: '21'
        distribution: 'temurin'
        cache: 'maven'

    - name: Run shard ${{ matrix.shard }} of 4
      run: |
        mvn test -Dgroups=e2e \
          -Dsurefire.failIfNoSpecifiedTests=false \
          -Dtest.shard.index=${{ matrix.shard }} \
          -Dtest.shard.total=4

    - name: Upload results for shard ${{ matrix.shard }}
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: allure-results-shard-${{ matrix.shard }}
        path: target/allure-results/

# Merge results от всех shard'ов
merge-results:
  runs-on: ubuntu-latest
  needs: [e2e-parallel]
  if: always()
  steps:
    - name: Download all shards
      uses: actions/download-artifact@v4
      with:
        pattern: allure-results-shard-*
        merge-multiple: true
        path: allure-results/
    # Генерация единого Allure отчёта...
```

**JUnit5 конфигурация для shard'инга:**
```java
// Кастомный TestExecutionListener для shard'инга
public class ShardFilter implements TestExecutionListener {
    // Или проще — через тег:
    // mvn test -Dgroups="shard1" для первого runner'а
    // mvn test -Dgroups="shard2" для второго
}
```

---

## Jenkins

### Вопрос 8. Как организовать Jenkinsfile для QA-pipeline?

```groovy
// Jenkinsfile (Declarative Pipeline)
pipeline {
    agent {
        docker {
            image 'maven:3.9.5-eclipse-temurin-21'
            args '-v /var/run/docker.sock:/var/run/docker.sock'  // для Testcontainers
        }
    }

    environment {
        MAVEN_OPTS = '-Xmx1g -Dmaven.repo.local=/tmp/.m2'
        BASE_URL   = credentials('staging-base-url')    // Jenkins Credentials
    }

    options {
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
    }

    stages {
        stage('Build') {
            steps {
                sh 'mvn compile -DskipTests --no-transfer-progress'
            }
        }

        stage('Tests') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh 'mvn test -Dgroups=unit --no-transfer-progress'
                    }
                    post {
                        always {
                            junit 'target/surefire-reports/TEST-*.xml'
                        }
                    }
                }

                stage('Integration Tests') {
                    steps {
                        sh 'mvn test -Dgroups=integration --no-transfer-progress'
                    }
                    post {
                        always {
                            junit 'target/surefire-reports/TEST-*.xml'
                        }
                    }
                }
            }
        }

        stage('E2E Tests') {
            when {
                anyOf {
                    branch 'main'
                    branch 'release/*'
                }
            }
            steps {
                sh """
                    mvn test \
                        -Dgroups=e2e \
                        -Dbase.url=${BASE_URL} \
                        --no-transfer-progress
                """
            }
        }

        stage('Allure Report') {
            steps {
                allure([
                    includeProperties: false,
                    jdk: '',
                    properties: [],
                    reportBuildPolicy: 'ALWAYS',
                    results: [[path: 'target/allure-results']]
                ])
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'target/allure-results/**', allowEmptyArchive: true
            cleanWs()    // очистить workspace
        }
        failure {
            // Уведомление в Slack
            slackSend(
                color: 'danger',
                message: "Pipeline FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}\n${env.BUILD_URL}"
            )
        }
        success {
            slackSend(
                color: 'good',
                message: "Pipeline PASSED: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
            )
        }
    }
}
```

---

## Паттерны тестирования в CI/CD

### Вопрос 9. Что такое Test Pyramid в контексте CI/CD?

```mermaid
graph TD
    subgraph Pyramid [Test Pyramid]
        E2E[E2E / UI Tests\n~10%\nМедленно, дорого\nCI: только main]
        INT[Integration Tests\n~20%\nTestcontainers, API\nCI: каждый PR]
        UNIT[Unit Tests\n~70%\nБыстро, дёшево\nCI: каждый commit]
    end

    subgraph Timing [Время выполнения]
        T1[Unit: < 2 мин]
        T2[Integration: < 10 мин]
        T3[E2E: < 30 мин]
    end

    UNIT --- T1
    INT --- T2
    E2E --- T3

    style UNIT fill:#4CAF50,color:#fff
    style INT fill:#FF9800,color:#fff
    style E2E fill:#F44336,color:#fff
```

**Стратегия запуска:**

| Событие | Unit | Integration | E2E | Smoke |
|---------|------|-------------|-----|-------|
| Push в feature-branch | ✅ | ✅ | ❌ | ❌ |
| PR в main | ✅ | ✅ | ✅ | ❌ |
| Merge в main | ✅ | ✅ | ✅ | ✅ |
| Деплой в staging | ❌ | ❌ | ❌ | ✅ |
| Деплой в production | ❌ | ❌ | ❌ | ✅ |
| Ночной прогон | ✅ | ✅ | ✅ | ✅ |

---

### Вопрос 10. Как настроить Allure history в CI/CD?

```yaml
# GitLab CI — сохранение истории Allure между запусками
allure-report:
  stage: report
  image: openjdk:21-slim
  before_script:
    - apt-get install -y wget unzip
    - wget -q https://github.com/allure-framework/allure2/releases/download/2.25.0/allure-2.25.0.tgz
    - tar -xzf allure-2.25.0.tgz
    - export PATH=$PATH:$(pwd)/allure-2.25.0/bin
  script:
    # Скачать историю из GitLab Pages (если есть)
    - |
      if curl -sf "$CI_PAGES_URL/allure-report/history/" -o /dev/null; then
        curl -sf "$CI_PAGES_URL/allure-report/history/" -o history.zip
        mkdir -p target/allure-results/history
        unzip -q history.zip -d target/allure-results/history
      fi
    # Сгенерировать отчёт с историей
    - allure generate target/allure-results --clean -o public/allure-report
  artifacts:
    paths:
      - public/
    expire_in: 30 days
  when: always

# GitHub Actions — через gh-pages branch
- name: Get Allure history
  uses: actions/checkout@v4
  if: always()
  continue-on-error: true
  with:
    ref: gh-pages
    path: gh-pages

- name: Generate Allure report with history
  uses: simple-elf/allure-report-action@master
  if: always()
  with:
    allure_results: target/allure-results
    allure_history: allure-history
    keep_reports: 20    # хранить последние 20 прогонов
```

---

### Вопрос 11. Как реализовать retry упавших тестов в CI?

```yaml
# Maven Surefire — retry на уровне JVM
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-surefire-plugin</artifactId>
    <configuration>
        <!-- Повторить упавший тест до 2 раз -->
        <rerunFailingTestsCount>2</rerunFailingTestsCount>
        <!-- Результат: FLAKY (если прошёл с повтором) или FAILURE -->
    </configuration>
</plugin>
```

```yaml
# GitLab CI — retry на уровне job'а
flaky-e2e-tests:
  script:
    - mvn test -Dgroups=e2e
  retry:
    max: 2
    when:
      - script_failure    # повторить при ошибке скрипта
      - runner_system_failure  # повторить при сбое runner'а

# GitHub Actions — retry на уровне step'а
- name: Run E2E tests
  uses: nick-fields/retry@v3
  with:
    timeout_minutes: 20
    max_attempts: 3
    command: mvn test -Dgroups=e2e
    on_retry_command: echo "Retry attempt..."
```

**Разделение flaky и реальных ошибок:**
```java
// Аннотация для известных flaky тестов
@Tag("flaky")
@RepeatedTest(3)    // запустить 3 раза, достаточно 1 прохождения
@DisplayName("Flaky: payment status polling")
void shouldPollPaymentStatus() {
    // нестабильный тест, требует рефакторинга
}
```

---

### Вопрос 12. Как настроить уведомления о результатах тестов?

```yaml
# GitHub Actions — уведомление в Slack
- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1.24.0
  with:
    payload: |
      {
        "text": "❌ Tests FAILED: ${{ github.repository }}",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Pipeline:* ${{ github.workflow }}\n*Branch:* `${{ github.ref_name }}`\n*Commit:* ${{ github.sha }}\n*By:* ${{ github.actor }}"
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {"type": "plain_text", "text": "View Run"},
                "url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
              }
            ]
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

```groovy
// Jenkins — Email уведомление
post {
    failure {
        emailext(
            subject: "FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                <h2>Pipeline Failed</h2>
                <p>Job: ${env.JOB_NAME}</p>
                <p>Build: #${env.BUILD_NUMBER}</p>
                <p>Failed tests:</p>
                ${currentBuild.rawBuild.getAction(AbstractTestResultAction.class)?.getFailedTests()
                    ?.collect { "<li>${it.fullName}</li>" }?.join('\n')}
                <p><a href="${env.BUILD_URL}">View Build</a></p>
            """,
            mimeType: 'text/html',
            recipientProviders: [developers(), requestor()]
        )
    }
}
```

---

### Вопрос 13. Что такое Shift-Left testing и как это реализовать в pipeline?

**Shift-Left** — перенос тестирования как можно раньше в цикл разработки, чтобы находить дефекты быстрее и дешевле.

```mermaid
timeline
    title Shift-Left: от позднего к раннему обнаружению
    section Традиционно
        Code Review : Написание кода
        QA Testing  : Отдельная фаза QA
        Bug Fixing  : Исправление найденных багов
    section Shift-Left
        Pre-commit  : Линтеры, форматирование
        Commit      : Unit тесты (< 1 мин)
        PR          : Integration + API тесты
        Merge       : E2E + Performance тесты
```

**Реализация:**
```yaml
# Pre-commit hooks (локально)
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: end-of-file-fixer
  - repo: local
    hooks:
      - id: unit-tests
        name: Unit Tests
        entry: mvn test -Dgroups=unit -q
        language: system
        pass_filenames: false

# Pipeline — быстрые тесты первыми
stages:
  - lint         # 1-2 мин: checkstyle, spotbugs
  - unit         # 2-3 мин: unit тесты
  - integration  # 5-10 мин: API, DB тесты
  - e2e          # 15-30 мин: UI тесты
```

---

### Вопрос 14. Как управлять секретами и конфигурацией в CI/CD?

```yaml
# НЕ делать так — секреты в коде!
# BASE_URL: "http://user:password@staging.example.com"

# GitLab CI — использовать CI/CD Variables (masked + protected)
variables:
  DB_PASSWORD: $DB_PASSWORD_SECRET    # определена в Settings > CI/CD > Variables

# GitHub Actions — использовать Secrets
env:
  DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
  API_KEY: ${{ secrets.API_KEY }}

# Jenkins — Credentials plugin
withCredentials([
    usernamePassword(
        credentialsId: 'staging-db',
        usernameVariable: 'DB_USER',
        passwordVariable: 'DB_PASSWORD'
    )
]) {
    sh 'mvn test -Ddb.user=$DB_USER -Ddb.password=$DB_PASSWORD'
}
```

**Передача конфигурации в тесты через Maven:**
```java
// В тесте читаем system property или env
@BeforeAll
static void configure() {
    String baseUrl = System.getProperty("base.url",
            System.getenv().getOrDefault("BASE_URL", "http://localhost:8080"));
    // ...
}
```

```xml
<!-- pom.xml — профили для окружений -->
<profiles>
    <profile>
        <id>staging</id>
        <properties>
            <base.url>https://staging.example.com</base.url>
            <test.groups>smoke,api</test.groups>
        </properties>
    </profile>
    <profile>
        <id>local</id>
        <activation><activeByDefault>true</activeByDefault></activation>
        <properties>
            <base.url>http://localhost:8080</base.url>
            <test.groups>unit,integration</test.groups>
        </properties>
    </profile>
</profiles>
```

**Запуск с профилем:**
```bash
mvn test -Pstaging
```

---

### Вопрос 15. Как публиковать Allure-отчёт в GitHub Pages / GitLab Pages?

```yaml
# GitHub Actions — полная настройка Allure с историей
name: E2E + Allure Report

on:
  push:
    branches: [main]

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  test-and-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: maven

      - name: Run tests
        run: mvn test --no-transfer-progress

      - name: Load previous Allure history
        uses: actions/checkout@v4
        if: always()
        continue-on-error: true
        with:
          ref: gh-pages
          path: gh-pages

      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        if: always()
        with:
          allure_results: target/allure-results
          allure_history: allure-history
          keep_reports: 30

      - name: Deploy to GitHub Pages
        if: always()
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: allure-history
          keep_files: true

# Отчёт будет доступен по адресу:
# https://<org>.github.io/<repo>/
```

---

## Чек-лист самопроверки

### CI/CD концепции
- [ ] Разница CI vs CD (Delivery) vs CD (Deployment)
- [ ] Quality Gate: критерии прохождения pipeline
- [ ] Test Pyramid: распределение типов тестов и когда запускать
- [ ] Shift-Left: перенос тестов на ранние этапы
- [ ] Artifacts vs Cache: что хранить и как долго

### GitLab CI
- [ ] Структура `.gitlab-ci.yml`: stages, jobs, cache, artifacts
- [ ] `when: manual`, `only`, `needs`, `parallel`
- [ ] Docker-in-Docker для Testcontainers
- [ ] GitLab Pages для Allure-отчёта
- [ ] CI/CD Variables: masked, protected

### GitHub Actions
- [ ] Структура workflow: on, jobs, steps
- [ ] `actions/setup-java` с кэшем Maven
- [ ] Matrix strategy для параллельных тестов
- [ ] Secrets и передача в тесты
- [ ] GitHub Pages деплой через `peaceiris/actions-gh-pages`

### Jenkins
- [ ] Declarative Pipeline: stages, post, options
- [ ] `parallel` для одновременных stage'ей
- [ ] Credentials plugin для секретов
- [ ] Allure plugin
- [ ] `when { branch 'main' }`

### Паттерны
- [ ] Retry: `rerunFailingTestsCount` в Surefire и retry в CI
- [ ] Allure history через gh-pages/artifacts
- [ ] Уведомления в Slack/Email при падении
- [ ] Maven профили для окружений
- [ ] Секреты: никогда не хранить в коде

---

## Ресурсы

**Документация:**
- [GitLab CI/CD docs](https://docs.gitlab.com/ee/ci/)
- [GitHub Actions docs](https://docs.github.com/en/actions)
- [Jenkins Pipeline docs](https://www.jenkins.io/doc/book/pipeline/)
- [Testcontainers in CI](https://java.testcontainers.org/supported_docker_environment/)

**Видео (YouTube):**
- "GitLab CI CD Tutorial for Beginners" — TechWorld with Nana
- "GitHub Actions Tutorial" — TechWorld with Nana
- "Jenkins Full Course" — Edureka
- "Allure Reports in CI/CD" — поиск на YouTube

---

[← Глава 11: Linux/Docker/K8s](11-linux-docker-k8s.md) | [Содержание](README.md) | [Глава 13: Алгоритмы →](13-algorithms.md)
