import time

N = 10_000_000

# List comprehension
start = time.time()
squares_comp = [i * i for i in range(N)]
end = time.time()
print("List comprehension:", end - start, "seconds")

# For loop
start = time.time()
squares_loop = []
for i in range(N):
    squares_loop.append(i * i)
end = time.time()
print("For loop:", end - start, "seconds")
