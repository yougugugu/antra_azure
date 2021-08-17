# Databricks notebook source
from pyspark.sql.functions import *
from pyspark.sql.types import *

# COMMAND ----------

movie_path = "/movieShop"
upload_path = "/FileStore"
raw_path = movie_path + '/raw'
bronze_path = movie_path + '/bronze'
silver_path = movie_path + '/silver'

# COMMAND ----------

spark.sql("USE movieshop")

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM movie_bronze

# COMMAND ----------

bronze_df = spark.read.table("movie_bronze").filter("status = 'new'")

# COMMAND ----------

genre_df = bronze_df.select(explode(col("movie.genres")).alias("genre"))
# display(genre_df)   

# COMMAND ----------

genre_df = genre_df.select(col("genre.*")).distinct()

# COMMAND ----------

""(
  genre_df.write
    .format("delta")
    .mode("append")
    .save(silver_path + "/genre")
)

# COMMAND ----------

movie_genre_df = bronze_df.select(col("movie.id").alias("movieid"),
                       explode(col("movie.genres")).alias("genre"))

# display(movie_genre_df)

# COMMAND ----------

movie_genre_df = movie_genre_df.select(col("movieid"),
                             col("genre.id").alias("genreid"))
# display(movie_genre_df)


# COMMAND ----------

(
movie_genre_df.write
  .format("delta")
  .mode("append")
  .save(silver_path + "/movie_genre"))

# COMMAND ----------

lan_df = (bronze_df.select(col("movie.originallanguage")).distinct()
      .select(monotonically_increasing_id().alias("id"), col("originallanguage")))
display(lan_df)

# COMMAND ----------

(
lan_df.write
  .format("delta")
  .mode("append")
  .save(silver_path + "/language")
)

# COMMAND ----------

bronze_path

# COMMAND ----------

new_bronze_df = (bronze_df.select(col("movie"),
                                 col("movie.*"))

                ) 


# COMMAND ----------

health_movie_df = new_bronze_df.filter(col("RunTime") >= 0).filter(col("Budget") > 1000000).groupBy("id").agg(count("id").alias("count")).filter(col("count")  < 2)

# COMMAND ----------

quarantine_movie_df.display()

# COMMAND ----------

health_movie_df = (
  health_movie_df
    .join(new_bronze_df, "id", "inner")
    .drop("count")
)

# COMMAND ----------



# COMMAND ----------

(health_movie_df
    .drop("movie")
    .drop("genres")
    .write
    .format("delta")
    .mode("append")
    .partitionBy("CreatedDate")
    .save(silver_path + "/movie")
)

# COMMAND ----------

spark.sql("""
DROP TABLE IF EXISTS health_movie
"""
)

spark.sql(f"""
CREATE TABLE health_movie
USING DELTA
LOCATION "{silver_path}/movie"
"""
         )

# COMMAND ----------

silver_status = health_movie_df.withColumn()

# COMMAND ----------

