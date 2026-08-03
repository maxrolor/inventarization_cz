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

    function logObjectMethods(obj, name) {
        console.log(`📌 Доступные свойства/методы объекта ${name}:`);
        const props = Object.getOwnPropertyNames(obj);
        for (let p of props) {
            if (typeof obj[p] === 'function') {
                console.log(`  ${p}()`);
            } else {
                console.log(`  ${p}: ${obj[p]}`);
            }
        }
        let proto = Object.getPrototypeOf(obj);
        while (proto && proto !== Object.prototype) {
            const protoProps = Object.getOwnPropertyNames(proto);
            for (let p of protoProps) {
                if (typeof proto[p] === 'function' && !props.includes(p)) {
                    console.log(`  (prototype) ${p}()`);
                }
            }
            proto = Object.getPrototypeOf(proto);
        }
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
                        const store = yield window.cadesplugin.CreateObjectAsync('CAdESCOM.Store');
                        yield store.Open(2, 'My', 0);

                        // 3. Найти сертификат с закрытым ключом
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

                        // 4. Создать подписанта и установить алгоритм
                        const signer = yield window.cadesplugin.CreateObjectAsync('CAdESCOM.CPSigner');
                        // Установка сертификата
                        if (typeof signer.propset_Certificate === 'function') {
                            yield signer.propset_Certificate(cert);
                        } else if (typeof signer.put_Certificate === 'function') {
                            yield signer.put_Certificate(cert);
                        } else {
                            signer.Certificate = cert;
                        }
                        // Алгоритм хеширования: 101 = ГОСТ 2012-256
                        if (typeof signer.propset_Algorithm === 'function') {
                            yield signer.propset_Algorithm(101);
                        } else if (typeof signer.put_Algorithm === 'function') {
                            yield signer.put_Algorithm(101);
                        } else {
                            signer.Algorithm = 101;
                        }
                        console.log('🔐 Алгоритм установлен');

                        // 5. Создать CadesSignedData
                        let signedData;
                        try {
                            signedData = yield window.cadesplugin.CreateObjectAsync('CAdESCOM.CadesSignedData');
                        } catch (e) {
                            signedData = yield window.cadesplugin.CreateObjectAsync('CAdESCOM.SignedData');
                        }
                        console.log('✅ SignedData создан');

                        // 6. Логируем доступные методы signedData
                        logObjectMethods(signedData, 'signedData');

                        // 7. Устанавливаем EncodingType = 0 (Base64)
                        if (typeof signedData.propset_EncodingType === 'function') {
                            yield signedData.propset_EncodingType(0);
                        } else if (typeof signedData.put_EncodingType === 'function') {
                            yield signedData.put_EncodingType(0);
                        } else {
                            signedData.EncodingType = 0;
                        }
                        console.log('✅ EncodingType = 0');

                        // 8. Устанавливаем Content
                        if (typeof signedData.propset_Content === 'function') {
                            yield signedData.propset_Content(data);
                        } else if (typeof signedData.put_Content === 'function') {
                            yield signedData.put_Content(data);
                        } else {
                            signedData.Content = data;
                        }
                        console.log('✅ Content установлен');

                        // 9. Пробуем установить Options = 0x1 (отключить TSA)
                        if (typeof signedData.propset_Options === 'function') {
                            yield signedData.propset_Options(0x1);
                            console.log('✅ Options установлен через propset_Options = 0x1');
                        } else if (typeof signedData.put_Options === 'function') {
                            yield signedData.put_Options(0x1);
                            console.log('✅ Options установлен через put_Options = 0x1');
                        } else if (typeof signedData.set_Options === 'function') {
                            yield signedData.set_Options(0x1);
                            console.log('✅ Options установлен через set_Options = 0x1');
                        } else {
                            try {
                                signedData.Options = 0x1;
                                console.log('✅ Options установлен напрямую = 0x1');
                            } catch (e) {
                                console.warn('Не удалось установить Options:', e);
                            }
                        }

                        // 10. Пробуем подписать
                        console.log('🔄 Вызов signedData.Sign(signer, false, 0)');
                        let signature = null;
                        try {
                            signature = yield signedData.Sign(signer, false, 0);
                            console.log('✅ Подпись создана через Sign(signer, false, 0)');
                        } catch (err) {
                            console.warn('❌ Sign(signer, false, 0) не сработал:', err.message || err);
                            try {
                                console.log('🔄 Пробуем signedData.Sign(signer, true, 0)');
                                signature = yield signedData.Sign(signer, true, 0);
                                console.log('✅ Подпись создана через Sign(signer, true, 0)');
                            } catch (err2) {
                                console.warn('❌ Sign(signer, true, 0) не сработал:', err2.message || err2);
                                try {
                                    console.log('🔄 Пробуем signedData.Sign(signer, false)');
                                    signature = yield signedData.Sign(signer, false);
                                    console.log('✅ Подпись создана через Sign(signer, false)');
                                } catch (err3) {
                                    console.warn('❌ Sign(signer, false) не сработал:', err3.message || err3);
                                    throw new Error('Не удалось создать подпись ни одним способом');
                                }
                            }
                        }

                        if (!signature) throw new Error('Подпись не получена');

                        console.log('✅ Подпись создана, длина:', signature.length);

                        // 11. Отправить подпись
                        const signResponse = yield fetch('/api/v1/proxy/auth-simple-sign-in', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ keyId: uuid, signature })
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
            const saveResponse = await fetch('/api/v1/auth/set-cz-token', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            });
            if (!saveResponse.ok) {
                const errData = await saveResponse.json();
                throw new Error(`Ошибка сохранения токена: ${errData.detail || saveResponse.statusText}`);
            }

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