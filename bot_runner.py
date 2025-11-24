import time
from usdt_bot import main

while True:
    try:
        main()
    except Exception as e:
        print("Bot crashed, restarting...", e)
        time.sleep(3)
