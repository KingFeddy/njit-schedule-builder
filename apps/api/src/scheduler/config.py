MAX_COURSES = 8       # Maximum courses in a single solve request
MAX_RESULTS = 10      # Maximum schedules returned to the client
EXPLORE_LIMIT = 25    # Backtracker stops after finding this many valid schedules
SOLVE_TIME_BUDGET_MS = 800   # Hard wall-clock limit per request (milliseconds)
NODE_CHECK_INTERVAL = 500    # Check the time budget every N nodes explored
