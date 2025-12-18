from textual.worker import WorkerState
print(dir(WorkerState))
try:
    print(f"SUCCESS: {WorkerState.SUCCESS}")
except:
    pass
try:
    print(f"COMPLETED: {WorkerState.COMPLETED}")
except:
    pass
try:
    print(f"FINISHED: {WorkerState.FINISHED}")
except:
    print("FINISHED not found")
