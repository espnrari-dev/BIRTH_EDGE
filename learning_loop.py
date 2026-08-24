import time
import learning
print("[learning_loop] starting")
while True:
    try:
        learning.update_outcomes(min_age_hours=0)
    except Exception as e:
        print(f"[learning_loop] error: {e}")
    time.sleep(300)
