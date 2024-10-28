# DESDEO web API

## Running the API

To run the API, invoke `uvicorn` as follows (assuming the current working directory is `desdeo/api`):

```shell
uvicorn --app-dir=./ app:app --reload
```