# Databricks notebook source
# MAGIC %run ./configuration

# COMMAND ----------

file_list = [[file.path, file.name] for file in dbutils.fs.ls(upload_path) if file.name.startswith("movie")]

# COMMAND ----------

for file in file_list:
  dbutils.fs.cp(file[0], raw_path + "/" +file[1])

# COMMAND ----------

dbutils.fs.ls(raw_path)

# COMMAND ----------

raw_movie_df = (spark.read
                .option("multiLine", "true")
                .json(raw_path))

# COMMAND ----------

# raw_movie_df.show(2)

# COMMAND ----------

new_movie_df = raw_movie_df.withColumn("movie", explode("movie"))
# new_movie_df.count()

# COMMAND ----------

# display(new_movie_df)
print("row count is", new_movie_df.count())

# COMMAND ----------

