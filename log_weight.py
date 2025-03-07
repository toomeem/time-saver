with open("text_files/weight.txt") as file:
  weight = file.readlines()

old_weight = [i.strip() for i in weight]
weight = []
month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

previous_date = old_weight[-1].split(":")[0]

while True:
  previous_date = previous_date.split("/")
  year = int(previous_date[0])
  month = int(previous_date[1])
  day = int(previous_date[2])
  if day == month_days[month - 1]:
    if month == 12:
      year += 1
      month = 1
    else:
      month += 1
    day = 1
  else:
    day += 1
  next_weight = input(f"{year}/{month}/{day}:")
  try:
    next_weight = float(next_weight)
    weight.append(f"{year}/{month}/{day}:{next_weight}\n")
    previous_date = weight[-1].split(":")[0]
  except ValueError:
    if next_weight == "exit":
      break
    previous_date = f"{year}/{month}/{day}"

with open("text_files/weight.txt", "a") as file:
  file.writelines(weight)
