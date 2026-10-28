FROM python:3.12-slim

WORKDIR /app

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin vouchers \
    && mkdir -p /app/output \
    && chown vouchers:vouchers /app/output

COPY main.py /app/main.py
COPY tiqets /app/tiqets

USER vouchers

ENTRYPOINT ["python", "main.py"]
