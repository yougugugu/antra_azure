# Databricks notebook source
# MAGIC %run ./ingest_raw

# COMMAND ----------

bronze_movie_df = 


# COMMAND ----------

display(bronze_movie_df)

# COMMAND ----------

(bronze_movie_df.write
  .format("delta")
  .mode("overwrite")
  .partitionBy("ingestdate")
  .save(bronze_path)
)

# COMMAND ----------

spark.sql("""
DROP TABLE IF EXISTS movie_bronze
""")

spark.sql(f"""
CREATE TABLE movie_bronze
USING delta
LOCATION "{bronze_path}"
""")

# COMMAND ----------

# MAGIC %sql
# MAGIC 
# MAGIC SELECT * FROM movie_bronze

# COMMAND ----------

dbutils.fs.rm(raw_path, True)

# COMMAND ----------

