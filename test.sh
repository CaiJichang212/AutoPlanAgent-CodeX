export PYTHONUNBUFFERED=1
cur_date=$(date "+%Y%m%d")
cur_time=$(date "+%H%M%S")
mkdir -p log/${cur_date}

source .venv/bin/activate
python main.py run "请分析中国A股光伏行业基本面情况？" \
    --auto-approve > log/${cur_date}/test_agent_${cur_time}.log 2>&1 &