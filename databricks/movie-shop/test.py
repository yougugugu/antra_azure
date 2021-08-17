# Databricks notebook source
# MAGIC %run ./main

# COMMAND ----------

assert read_table("movie_silver").count() == 9992, "Duplicate values are not cleaned"

# COMMAND ----------

assert read_table("movie_bronze").filter(col("status") != 'loaded').count() == 0, "Quarantined values are not cleaned"

# COMMAND ----------

assert read_table("movie_silver").filter(col("budget") < 1000000).count() == 0, "Budget less than 1000000 values are not cleaned"

# COMMAND ----------

assert read_table("movie_silver").filter(col("runtime") < 0).count() == 0, "Runtime less than 0 values are not cleaned"

# COMMAND ----------

assert read_table("genre_silver").filter(col("name") == '').count() == 0, "Null values are not cleaned"

# COMMAND ----------

