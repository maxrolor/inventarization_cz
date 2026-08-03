document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('getTokenBtn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    let pluginer = null;
    let certificate = null;

    async function initPluginer() {
        try {
            if (typeof CadesPluginer === 'undefined') {
                throw new Error('Библиотека CadesPluginer не загружена. Проверьте подключение скрипта.');
            }
            
            // ОБРАТИТЕ ВНИМАНИЕ: ВАЖНОЕ ИСПРАВЛЕНИЕ ТУТ
            // Берем конструктор, даже если он спрятан внутри объекта default
            const CadesPluginerConstructor = CadesPluginer.default || CadesPluginer;
            
            pluginer = new CadesPluginerConstructor();
            await pluginer.init();
            return true;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка инициализации плагина: ${e.message}</div>`;
            console.error(e);
            return false;
        }
    }

    async function getCertificate() {
        try {
            const certs = await pluginer.getCertificates();
            if (!certs || certs.length === 0) {
                throw new Error('Сертификаты не найдены. Убедитесь, что КриптоПРО установлен и сертификат доступен.');
            }
            // Для простоты берём первый. Можно реализовать выбор через модальное окно.
            certificate = certs[0];
            statusDiv.innerHTML = `<div class="alert alert-info">Выбран сертификат: ${certificate.subjectName || certificate.serialNumber}</div>`;
            return certificate;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка получения сертификатов: ${e.message}</div>`;
            return null;
        }
    }

    async function getAuthKey() {
        try {
            const response = await fetch('/api/v1/proxy/auth-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка получения ключа: ${response.status} - ${errorText}`);
            }
            const data = await response.json();
            return data;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка запроса /auth/key: ${e.message}</div>`;
            return null;
        }
    }

    async function signData(data) {
        try {
            const signature = await pluginer.sign(
                data,
                certificate.serialNumber,
                'base64'
            );
            return signature;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка подписания: ${e.message}</div>`;
            return null;
        }
    }

    async function sendSignIn(uuid, signedData, inn = null) {
        try {
            const payload = {
                uuid: uuid,
                data: signedData,
                unitedToken: false
            };
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
            const result = await response.json();
            return result.token;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка получения токена: ${e.message}</div>`;
            return null;
        }
    }

    async function saveTokenOnServer(token) {
        try {
            const response = await fetch('/api/v1/auth/set-cz-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка сохранения токена: ${response.status} - ${errorText}`);
            }
            const result = await response.json();
            return result;
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка сохранения токена на сервере: ${e.message}</div>`;
            return null;
        }
    }

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.textContent = 'Выполняется...';
        statusDiv.innerHTML = '';
        resultDiv.innerHTML = '';

        try {
            const initOk = await initPluginer();
            if (!initOk) return;

            const cert = await getCertificate();
            if (!cert) return;

            const keyData = await getAuthKey();
            if (!keyData) return;
            const { uuid, data } = keyData;

            statusDiv.innerHTML = `<div class="alert alert-info">Подписываем данные...</div>`;
            const signedData = await signData(data);
            if (!signedData) return;

            statusDiv.innerHTML = `<div class="alert alert-info">Получаем токен...</div>`;
            const token = await sendSignIn(uuid, signedData);
            if (!token) return;

            statusDiv.innerHTML = `<div class="alert alert-success">Токен получен. Сохраняем...</div>`;
            const saveResult = await saveTokenOnServer(token);
            if (saveResult) {
                resultDiv.innerHTML = `<div class="alert alert-success">Токен успешно сохранён! Страница будет обновлена...</div>`;
                // Обновляем страницу через 2 секунды, чтобы показать актуальный статус
                setTimeout(() => location.reload(), 2000);
            }
        } catch (e) {
            statusDiv.innerHTML = `<div class="alert alert-danger">Ошибка: ${e.message}</div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = 'Получить токен';
        }
    });
});