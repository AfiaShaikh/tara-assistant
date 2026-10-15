FROM python:3.12-slim
WORKDIR /project
COPY Code/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY Code /project/Code
COPY Input_Data /project/Input_Data
COPY Model_Prompts_Config /project/Model_Prompts_Config
COPY Evaluation_Results /project/Evaluation_Results
ENV TARA_HOST=0.0.0.0
EXPOSE 8000
CMD ["python", "Code/run.py"]
