FROM eclipse-temurin:21-jre-jammy

ARG JENA_VERSION=6.2.0
ARG JENA_SHA512=ba65f5867d2d4741b2ed9e2af5a0d4fbb447909894ab2a0c6bc4dac8997f4fe339c87b13c48d45d054977769f0f8bf763ea346b1f7792d5cdc458041bd43a132

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl \
    && curl --fail --silent --show-error --location \
        --output /tmp/apache-jena-fuseki.tar.gz \
        "https://archive.apache.org/dist/jena/binaries/apache-jena-fuseki-${JENA_VERSION}.tar.gz" \
    && echo "${JENA_SHA512}  /tmp/apache-jena-fuseki.tar.gz" | sha512sum --check --strict \
    && mkdir --parents /opt/fuseki /fuseki-base/databases \
    && tar --extract --gzip --file /tmp/apache-jena-fuseki.tar.gz \
        --directory /opt/fuseki --strip-components=1 \
    && rm /tmp/apache-jena-fuseki.tar.gz \
    && rm --recursive --force /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 fuseki \
    && useradd --system --uid 10001 --gid fuseki --home-dir /fuseki-base fuseki \
    && chown --recursive fuseki:fuseki /fuseki-base

COPY docker/fuseki/entrypoint.sh /usr/local/bin/problem-bank-fuseki

RUN chmod 0755 /usr/local/bin/problem-bank-fuseki

ENV FUSEKI_HOME=/opt/fuseki \
    FUSEKI_BASE=/fuseki-base

USER fuseki
WORKDIR /opt/fuseki

EXPOSE 3030

ENTRYPOINT ["/usr/local/bin/problem-bank-fuseki"]
