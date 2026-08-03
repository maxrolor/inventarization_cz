// app/static/js/cz_auth.js

(function() {
    'use strict';

    const getTokenBtn = document.getElementById('getTokenBtn');
    const statusDiv = document.getElementById('status');
    const resultDiv = document.getElementById('result');

    if (!getTokenBtn) return;

    function setStatus(msg, err = false) {
        statusDiv.innerHTML = `<div class="alert ${err ? 'alert-danger' : 'alert-info'}">${msg}</div>`;
    }

    function setResult(msg, err = false) {
        resultDiv.innerHTML = `<div class="alert ${err ? 'alert-danger' : 'alert-success'}">${msg}</div>`;
    }

    async function getCzToken() {
        setStatus('Инициализация плагина...');
        setResult('');

        try {
            if (typeof window.cadesplugin === 'undefined') {
                throw new Error('Плагин КриптоПРО CAdES не найден.');
            }

            window.cadesplugin_load_timeout = 60000;

            if (typeof window.cadesplugin.then === 'function') {
                await window.cadesplugin;
                console.log('✅ Плагин инициализирован');
            }

            if (typeof window.cadesplugin.async_spawn !== 'function') {
                throw new Error('Метод async_spawn не найден.');
            }

            setStatus('Запрос ключа сессии...');
            const token = await new Promise((resolve, reject) => {
                window.cadesplugin.async_spawn(function* () {
                    try {
                        // 1. Получить keyId
                        const keyResponse = yield fetch('/api/v1/proxy/auth-key', {
                            method: 'GET',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        if (!keyResponse.ok) {
                            const errText = yield keyResponse.text();
                            throw new Error(`Ошибка получения ключа: ${keyResponse.status} - ${errText}`);
                        }
                        const keyData = yield keyResponse.json();
                        const uuid = keyData.uuid;
                        const data = keyData.data;
                        console.log('🆔 uuid:', uuid);
                        console.log('📊 data:', data);

                        // 2. Открыть хранилище
                        const store = yield cadesplugin.CreateObjectAsync('CAdESCOM.Store');
                        yield store.Open(cadesplugin.CAPICOM_CURRENT_USER_STORE, cadesplugin.CAPICOM_MY_STORE,
                            cadesplugin.CAPICOM_STORE_OPEN_MAXIMUM_ALLOWED);

                        const certs = yield store.Certificates;
                        const count = yield certs.Count;
                        let cert = null;
                        for (let i = 1; i <= count; i++) {
                            const c = yield certs.Item(i);
                            const hasKey = yield c.HasPrivateKey();
                            if (hasKey) {
                                cert = c;
                                break;
                            }
                        }
                        if (!cert) {
                            throw new Error('Не найден сертификат с закрытым ключом');
                        }
                        console.log('✅ Сертификат выбран:', yield cert.SubjectName);

                        // 3. Создать подписанта
                        const signer = yield cadesplugin.CreateObjectAsync('CAdESCOM.CPSigner');
                        yield signer.propset_Certificate(cert);
                        yield signer.propset_CheckCertificate(true);

                        // 4. Создать CadesSignedData (присоединённая подпись)
                        const signedData = yield cadesplugin.CreateObjectAsync('CAdESCOM.CadesSignedData');
                        yield signedData.propset_Content(data);
                        console.log('✍️ Content = data (строка)');

                        // 5. Присоединённая подпись (detached = false)
                        console.log('🔄 Вызов SignCades (detached = false)...');
                        let signature;
                        try {
                            signature = yield signedData.SignCades(signer, cadesplugin.CADESCOM_CADES_BES, false);
                        } catch (err) {
                            const e = cadesplugin.getLastError(err);
                            console.error('Ошибка при создании подписи:', e);
                            throw new Error('Не удалось создать подпись: ' + e);
                        }
                        console.log('✅ Подпись создана, длина:', signature.length);

                        // 6. Отправить подпись
                        const signResponse = yield fetch('/api/v1/proxy/auth-simple-sign-in', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                uuid: uuid,
                                data: signature
                            })
                        });
                        if (!signResponse.ok) {
                            const errText = yield signResponse.text();
                            throw new Error(`Ошибка авторизации: ${signResponse.status} - ${errText}`);
                        }
                        const tokenData = yield signResponse.json();
                        const authToken = tokenData.token;
                        if (!authToken) throw new Error('Сервер не вернул токен');
                        console.log('✅ Токен получен');
                        resolve(authToken);
                    } catch (err) {
                        console.error('❌ Ошибка в async_spawn:', err);
                        reject(err);
                    }
                });
            });

            setStatus('Сохранение токена...');
            // Исправленный путь (без /api/v1)
            const saveResponse = await fetch('/auth/set-cz-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            if (!saveResponse.ok) {
                let errText;
                try {
                    const errData = await saveResponse.json();
                    errText = errData.detail || saveResponse.statusText;
                } catch (e) {
                    errText = await saveResponse.text();
                }
                throw new Error(`Ошибка сохранения токена: ${saveResponse.status} - ${errText}`);
            }
            const saveResult = await saveResponse.json();
            console.log('✅ Токен сохранён:', saveResult);

            setResult('✅ Токен успешно получен и сохранён!');
            setStatus('Готово');
            setTimeout(() => window.location.reload(), 1500);

        } catch (error) {
            console.error('❌ Ошибка получения токена:', error);
            setStatus('Ошибка: ' + error.message, true);
            setResult('❌ ' + error.message, true);
        }
    }

    getTokenBtn.addEventListener('click', getCzToken);
})();