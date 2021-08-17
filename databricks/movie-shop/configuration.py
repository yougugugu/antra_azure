# Databricks notebook source
movie_path = "/movieshop"
upload_path = "/FileStore"
raw_path = movie_path + '/01_raw'
bronze_path = movie_path + '/02_bronze'
silver_path = movie_path + '/03_silver'
movie_bronze_path = bronze_path  + '/movie'
genre_silver_path = silver_path + '/genre'
movie_genre_silver_path = silver_path + '/movie_genre'
language_silver_path = silver_path + '/language'
movie_silver_path = silver_path + '/movie'

# COMMAND ----------

dbutils.fs.rm(movie_path, True)

# COMMAND ----------

dbutils.fs.mkdirs(movie_path)
print("movieshop folder created")

# COMMAND ----------

dbutils.fs.mkdirs(raw_path)
print("raw folder created")

# COMMAND ----------

dbutils.fs.mkdirs(bronze_path)
print("bronze folder created")

# COMMAND ----------

dbutils.fs.mkdirs(silver_path)
print("silver folder created")

# COMMAND ----------

spark.sql("CREATE DATABASE IF NOT EXISTS movieshop")
spark.sql("USE movieshop")
print("movieshop database created")