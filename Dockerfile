FROM python:3.11-slim

WORKDIR /app
COPY . /app

# stdlib only -- nothing to install. Run the test suite at build time so a
# broken image fails to build instead of failing silently at run time.
RUN python3 -m unittest discover -s tests -v

CMD ["python3", "run_demo.py"]
