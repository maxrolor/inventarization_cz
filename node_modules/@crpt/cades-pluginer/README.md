# cades-pluginer

[![Travis][build-badge]][build]
[![npm package][npm-badge]][npm]
[![Coveralls][coveralls-badge]][coveralls]

CADES Pluginer already contains cadesplugin_api.js in own bundle.

## Usage

```javascript

import { CadesPluginer as anyName } from "@crpt/cades-pluginer";
//or
import CadesPluginer from "@crpt/cades-pluginer";
//usually you will need 2 methods

CadesPluginer.getFinalCertsArray().then(certs => {
  console.log("certs", certs);
  CadesPluginer.signMessage("lalala", certs[0].certificate).then(signed =>
    console.log("signed", signed);
  );
});

```

| method | description |
|---|---|
| getFinalCertsArray(): Promise<Cert[]> | Init plugin, create store, . Cert: {certificate: {}, info: [] }, certificate is an original cadesplugin Certificate object,  info is an array [name, date_from, date_to, serial_number]. |
| signMessage(message, cert, detached): Promise<string>| Sign message with selected certificate. |

[build-badge]: https://img.shields.io/travis/user/repo/master.png?style=flat-square
[build]: https://travis-ci.org/user/repo

[npm-badge]: https://img.shields.io/npm/v/npm-package.png?style=flat-square
[npm]: https://www.npmjs.org/package/npm-package

[coveralls-badge]: https://img.shields.io/coveralls/user/repo/master.png?style=flat-square
[coveralls]: https://coveralls.io/github/user/repo
