.. _aio-openapi-env:


======================
 Environment Variables
======================

Several environment variables can be configured at application level

* **DATASTORE** Connection string for postgresql database
* **BAD_DATA_MESSAGE** (Invalid data format), message displayed when data is not in valid format (not JSON for example)
* **ERROR_500_MESSSAGE** (Internal Server Error), message displayed when things go wrong
* **DBPOOL_MAX_SIZE** (10), maximum number of connections in postgres connection pool
* **DBECHO**, if set to `true` or `yes` it will use `echo=True` when setting up sqlalchemy engine
* **MICRO_SERVICE_PORT** (8080), default port when running the `serve` command
* **MICRO_SERVICE_HOST** (0.0.0.0), default host when running the `serve` command
* **MAX_PAGINATION_LIMIT** (100), maximum number of objects displayed at once
* **DEF_PAGINATION_LIMIT** (50), default value of pagination
* **SPEC_ROUTE** (/spec), path of OpenAPI spec doc (JSON)
