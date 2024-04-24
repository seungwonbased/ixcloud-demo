#!/bin/sh
# shellcheck disable=SC2164
cd /dummy

flask db init
flask db migrate
flask db upgrade

python3 -m flask run --host=0.0.0.0