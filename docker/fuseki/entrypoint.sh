#!/bin/sh

set -eu

server_pid=""

stop_server() {
    if [ -n "$server_pid" ] && kill -0 "$server_pid" 2>/dev/null; then
        kill -TERM "$server_pid"
        wait "$server_pid" || true
    fi
}

trap stop_server INT TERM

/opt/fuseki/fuseki-server \
    --config=/fuseki-config/config.ttl \
    --port=3030 \
    --ping &
server_pid=$!

attempt=0
until curl --fail --silent --show-error "http://127.0.0.1:3030/\$/ping" >/dev/null; do
    if ! kill -0 "$server_pid" 2>/dev/null; then
        wait "$server_pid"
        exit $?
    fi

    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "Fuseki가 60초 안에 준비되지 않았습니다." >&2
        stop_server
        exit 1
    fi

    sleep 1
done

seed_marker=/fuseki-base/databases/.example-loaded
if [ ! -f "$seed_marker" ]; then
    echo "정보처리기사 예제 그래프를 최초 적재합니다."
    if ! curl --fail --silent --show-error \
        --request POST \
        --header "Content-Type: text/turtle" \
        --data-binary @/ontology/examples/information-processing-engineer.ttl \
        "http://127.0.0.1:3030/problem-bank/data?default"; then
        echo "예제 그래프를 적재하지 못했습니다." >&2
        stop_server
        exit 1
    fi
    touch "$seed_marker"
fi

echo "Fuseki 준비 완료: http://localhost:3030/#/dataset/problem-bank/query"
wait "$server_pid"
