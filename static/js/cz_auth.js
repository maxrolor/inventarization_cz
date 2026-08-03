// app/static/js/cz_auth.js

document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('getTokenBtn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    let cades = null;      // будет хранить объект плагина после инициализации
    let certificate = null;

    // ---------- Инициализация плагина ----------
    async function initPluginer() {
        try {
            console.log("⏳ Ожидаем загрузку window.cadesplugin...");

            if (typeof window.cadesplugin === 'undefined') {
                throw new Error('Расширение КриптоПРО не найдено в браузере. Проверьте, включено ли оно.');
            }

            // window.cadesplugin — это Promise, который разрешается в объект плагина
            const plugin = await window.cadesplugin;
            console.log("✅ Промис window.cadesplugin успешно разрешён!");
            console.log("🔍 Доступные методы плагина:", Object.keys(plugin));

            // Сохраняем ссылку на плагин
            cades = plugin;

            // Проверяем наличие методов создания объектов
            if (typeof cades.CreateObjectAsync === 'function') {
                console.log("✅ Найден асинхронный метод CreateObjectAsync");
                // Если есть метод init, вызываем его
                if (typeof cades.init === 'function') {
                    await cades.init();
                }
                return true;
            } else if (typeof cades.CreateObject === 'function') {
                console.log("✅ Найден синхронный метод CreateObject");
                if (typeof cades.init === 'function') {
                    await cades.init();
                }
                return true;
            } else {
                throw new Error('Метод CreateObject или CreateObjectAsync не найден в плагине');
            }
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">❌ Ошибка инициализации: ${e.message}</div>`;
            console.error(e);
            return false;
        }
    }

    // ---------- Универсальное создание COM-объектов (асинхронное) ----------
    async function createObject(progId) {
        // Приоритет у асинхронного метода (современные браузеры)
        if (typeof cades.CreateObjectAsync === 'function') {
            return await cades.CreateObjectAsync(progId);
        } else if (typeof cades.CreateObject === 'function') {
            // Для старых версий (IE, NPAPI) используем синхронный вызов
            return cades.CreateObject(progId);
        } else {
            throw new Error('Нет доступных методов создания объектов');
        }
    }

    // ---------- Получение сертификата ----------
    async function getCertificate() {
        try {
            console.log("📂 Создаём Store через createObject('CAdESCOM.Store')...");
            const store = await createObject('CAdESCOM.Store');

            // Открываем хранилище My (личные сертификаты) — параметры: StoreLocation, StoreName, OpenMode
            // CAPICOM_CURRENT_USER_STORE = 2, CAPICOM_MY_STORE = "My", CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED = 2
            store.Open(2, "My", 2);

            const certCount = store.Certificates.Count;
            console.log(`✅ Найдено сертификатов: ${certCount}`);

            if (!certCount || certCount === 0) {
                throw new Error('Сертификаты не найдены. Убедитесь, что токен вставлен и CSP запущен.');
            }

            // Берём первый сертификат (для выбора можно реализовать диалог)
            certificate = store.Certificates.Item(1);
            statusDiv.innerHTML = `<div class="alert alert-info">Выбран сертификат: ${certificate.SubjectName || certificate.SerialNumber}</div>`;
            return certificate;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка получения сертификатов: ${e.message}</div>`;
            console.error(e);
            return null;
        }
    }

    // ---------- Запрос ключа через прокси ----------
    async function getAuthKey() {
        try {
            const response = await fetch('/api/v1/proxy/auth-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка ключа: ${response.status} - ${errorText}`);
            }
            return await response.json();
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка /auth/key: ${e.message}</div>`;
            return null;
        }
    }

    // ---------- Подписание данных ----------
    async function signData(data) {
        try {
            console.log("✍️ Подписываем данные...");

            // Создаём подписывающего
            const signer = await createObject('CAdESCOM.CPSigner');
            signer.Certificate = certificate;

            // Создаём объект данных для подписи
            const signedDataObj = await createObject('CAdESCOM.CadesSignedData');
            // Устанавливаем кодировку содержимого (1 = CADESCOM_BASE64_TO_BINARY)
            signedDataObj.ContentEncoding = 1;
            signedDataObj.Content = data;

            // Подписываем (1 = CADESCOM_CADES_BES, false = откреплённая подпись не нужна)
            const signature = signedDataObj.SignCades(signer, 1, false);
            return signature;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка подписания: ${e.message}</div>`;
            console.error(e);
            return null;
        }
    }

    // ---------- Отправка подписи и получение токена ----------
    async function sendSignIn(uuid, signedData, inn = null) {
        try {
            const payload = { uuid, data: signedData, unitedToken: false };
            if (inn) payload.inn = inn;

            const response = await fetch('/api/v1/proxy/auth-simple-sign-in', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка аутентификации: ${response.status} - ${errorText}`);
            }
            return (await response.json()).token;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка токена: ${e.message}</div>`;
            return null;
        }
    }

    // ---------- Сохранение токена на сервере ----------
    async function saveTokenOnServer(token) {
        try {
            const response = await fetch('/api/v1/auth/set-cz-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка сохранения: ${response.status} - ${errorText}`);
            }
            return await response.json();
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка сохранения: ${e.message}</div>`;
            return null;
        }
    }

    // ---------- Обработчик кнопки ----------
    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Выполняется...';
        statusDiv.innerHTML = '';
        resultDiv.innerHTML = '';

        try {
            // 1. Инициализация плагина
            if (!(await initPluginer())) return;

            // 2. Получение сертификата
            if (!(await getCertificate())) return;

            // 3. Получение ключа от ЧЗ
            const keyData = await getAuthKey();
            if (!keyData) return;
            const { uuid, data } = keyData;

            // 4. Подписание данных
            statusDiv.innerHTML = `<div class="alert alert-info">Подписываем данные...</div>`;
            const signedData = await signData(data);
            if (!signedData) return;

            // 5. Получение токена
            statusDiv.innerHTML = `<div class="alert alert-info">Получаем токен...</div>`;
            const token = await sendSignIn(uuid, signedData);
            if (!token) return;

            // 6. Сохранение токена на сервере
            statusDiv.innerHTML = `<div class="alert alert-success">Токен получен. Сохраняем...</div>`;
            const saveResult = await saveTokenOnServer(token);
            if (saveResult) {
                resultDiv.innerHTML = `<div class="alert alert-success">Токен успешно сохранён! Страница обновится...</div>`;
                setTimeout(() => location.reload(), 2000);
            }
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка: ${e.message}</div>`;
            console.error(e);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Получить токен';
        }
    });
});