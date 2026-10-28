FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin vouchers \
    && mkdir -p /app/data/output \
    && chown vouchers:vouchers /app/data/output

COPY main.py /app/main.py
COPY tiqets /app/tiqets

USER vouchers

ENTRYPOINT ["python", "main.py"]
