# Databricks notebook source
# MAGIC %run ./configuration

# COMMAND ----------

# MAGIC %run ./functions

# COMMAND ----------

# MAGIC %md
# MAGIC # read data

# COMMAND ----------

move_raw(upload_path, raw_path)

# COMMAND ----------

schema = StructType([
                   StructField("movie", ArrayType(StructType([
                                                 StructField("BackdropUrl", StringType()),
                                                 StructField("Budget", DoubleType()),
                                                 StructField("CreatedDate", TimestampType()),
                                                 StructField("Id", LongType()),
                                                 StructField("ImdbUrl", StringType()),
                                                 StructField("OriginalLanguage", StringType()),
                                                 StructField("Overview", StringType()),
                                                 StructField("PosterUrl", StringType()),
                                                 StructField("Price", DoubleType()),
                                                 StructField("ReleaseDate", TimestampType()),
                                                 StructField("Revenue", DoubleType()),
                                                 StructField("RunTime", LongType()),
                                                 StructField("Tagline", StringType()),
                                                 StructField("Title", StringType()),
                                                 StructField("TmdbUrl", StringType()),
                                                 StructField("UpdatedBy", StringType()),
                                                 StructField("UpdatedDate", TimestampType()),
                                                 StructField("genres", ArrayType(StructType([
                                                                                  StructField("id", LongType()),
                                                                                  StructField("name", StringType())
                                                                                  ])))
                     ])), True)])

# COMMAND ----------

movie_raw = read_raw(raw_path, schema)

# COMMAND ----------

movie_explode = explode_bronze(movie_raw, "movie", "value").distinct()

# COMMAND ----------

# MAGIC %md
# MAGIC # add metadata

# COMMAND ----------

movie_bronze = add_metadata(movie_explode)

# COMMAND ----------

write_delta(movie_bronze).partitionBy("ingestdate").save(movie_bronze_path)

# COMMAND ----------

register_table("movie_bronze", movie_bronze_path)

# COMMAND ----------

dbutils.fs.rm(raw_path, True)

# COMMAND ----------

movie_bronze_df = read_table("movie_bronze")

# COMMAND ----------

transformed_movie_df = transform_bronze(movie_bronze_df, "value")

# COMMAND ----------

# MAGIC %md
# MAGIC # genres

# COMMAND ----------

genre_df = (
  explode_bronze(transformed_movie_df, "genres", "genres")
    .distinct()
)

# COMMAND ----------

genre_bronze_df = add_metadata(genre_df)

# COMMAND ----------

write_delta(genre_bronze_df).partitionBy("ingestdate").save(genre_bronze_path)
register_table("genre_bronze", genre_bronze_path)

# COMMAND ----------

genre_bronze_df = read_table("genre_bronze")

# COMMAND ----------

transformed_genre_df = transform_bronze(genre_bronze_df, "genres")

# COMMAND ----------

clean_genre_df = filter_null(transformed_genre_df, "name")[1]
quarantine_genre_df = filter_null(transformed_genre_df, "name")[0]

# COMMAND ----------

write_delta(clean_genre_df, ["genres"]).save(genre_silver_path)

# COMMAND ----------

update_bronze_status(spark, genre_bronze_path, clean_genre_df, "genres", "loaded")

# COMMAND ----------

update_bronze_status(spark, genre_bronze_path, quarantine_genre_df, "genres", "quarantined")

# COMMAND ----------

register_table("genre_silver", genre_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC # movie_genres

# COMMAND ----------

movie_genre_df = explode_bronze(transformed_movie_df, "genres", "genres", ["Id"])

# COMMAND ----------

movie_genre_df = movie_genre_df.select(row_number().over(Window.orderBy(col("id"))).alias("moviegenreid"),
                                      col("id").alias("movieid"),
                                      col("genres.id").alias("genreid"))

# COMMAND ----------

movie_genre_bronze_df = add_metadata(movie_genre_df)

# COMMAND ----------

write_delta(movie_genre_bronze_df).partitionBy("ingestdate").save(movie_genre_bronze_path)
register_table("movie_genre_bronze", movie_genre_bronze_path)

# COMMAND ----------

movie_genre_bronze_df = read_table("movie_genre_bronze")

# COMMAND ----------

transformed_movie_genre_df = movie_genre_bronze_df.select(col("moviegenreid"),
                                                          col("movieid"),
                                                          col("genreid"))

# COMMAND ----------

write_delta(transformed_movie_genre_df).save(movie_genre_silver_path)

# COMMAND ----------

update_bronze_status(spark, movie_genre_bronze_path, transformed_movie_genre_df, "moviegenreid", "loaded")

# COMMAND ----------

register_table("movie_genre_silver", movie_genre_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC # language

# COMMAND ----------

language_df = (transformed_movie_df.select(col("OriginalLanguage").alias("language"))
            .distinct()
            .select(row_number().over(Window.orderBy(col("language"))).alias("languageid"),
                  col("language")))

# COMMAND ----------

language_bronze_df = add_metadata(language_df)

# COMMAND ----------

write_delta(language_bronze_df).partitionBy("ingestdate").save(language_bronze_path)
register_table("language_bronze", language_bronze_path)

# COMMAND ----------

language_bronze_df = read_table("language_bronze")

# COMMAND ----------

transformed_language_df = language_bronze_df.select(col("languageid"),
                                                      col("language"))

# COMMAND ----------

write_delta(transformed_language_df).save(language_silver_path)
update_bronze_status(spark, language_bronze_path,transformed_language_df, "languageid", "loaded")

# COMMAND ----------

register_table("language_silver", language_silver_path)

# COMMAND ----------

# MAGIC %md 
# MAGIC # filter runtime < 0

# COMMAND ----------

movie_bronze_df = read_table("movie_bronze")
transformed_movie_df = transform_bronze(movie_bronze_df, "value")

# COMMAND ----------

runtime_quarantine_movie_df = filter_less_than(transformed_movie_df, "RunTime", 0)[0]
runtime_clean_movie_df = filter_less_than(transformed_movie_df, "RunTime", 0)[1]

# COMMAND ----------

runtime_quarantine_movie_df = remove_genres_change_language(runtime_quarantine_movie_df)
runtime_clean_movie_df = remove_genres_change_language(runtime_clean_movie_df)

# COMMAND ----------

write_delta(runtime_clean_movie_df, ["value"]).partitionBy("CreatedDate").save(movie_silver_path)

# COMMAND ----------

update_bronze_status(spark, movie_bronze_path, runtime_clean_movie_df, "value", "loaded")

# COMMAND ----------

update_bronze_status(spark, movie_bronze_path, runtime_clean_movie_df, "value", "quarantined")

# COMMAND ----------

runtime_quarantine_movie_df = get_quarantined_df("movie_bronze")

# COMMAND ----------

runtime_repair_movie_df = runtime_quarantine_movie_df.withColumn("RunTime", abs(col("RunTime")))
runtime_repair_movie_df = remove_genres_change_language(runtime_repair_movie_df)

# COMMAND ----------

write_delta(runtime_repair_movie_df, ["value"]).partitionBy("CreatedDate").save(movie_silver_path)

# COMMAND ----------

update_bronze_status(spark, movie_bronze_path, runtime_repair_movie_df, "value", "loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC # budget less than

# COMMAND ----------

movie_bronze_df = read_table("movie_bronze")
transformed_movie_df = transform_bronze(movie_bronze_df, "value")

# COMMAND ----------

budget_quarantine_movie_df = filter_less_than(transformed_movie_df, "Budget", 1000000)[0]
budget_clean_movie_df = filter_less_than(transformed_movie_df, "Budget", 1000000)[1]

# COMMAND ----------

budget_quarantine_movie_df = remove_genres_change_language(budget_quarantine_movie_df)
budget_clean_movie_df = remove_genres_change_language(budget_clean_movie_df)

# COMMAND ----------

write_delta(budget_clean_movie_df, ["value"], "overwrite").partitionBy("CreatedDate").save(movie_silver_path)
update_bronze_status(spark, movie_bronze_path, budget_clean_movie_df, "value", "loaded")

# COMMAND ----------

update_bronze_status(spark, movie_bronze_path, budget_clean_movie_df, "value", "quarantined")

# COMMAND ----------

budget_quarantine_movie_df = get_quarantined_df("movie_bronze")

# COMMAND ----------

budget_repair_movie_df =budget_quarantine_movie_df.withColumn("RunTime", lit(1000000).cast("Long"))
budget_repair_movie_df = remove_genres_change_language(budget_repair_movie_df)

# COMMAND ----------

write_delta(budget_repair_movie_df, ["value"]).partitionBy("CreatedDate").save(movie_silver_path)
update_bronze_status(spark, movie_bronze_path, budget_repair_movie_df, "value", "loaded")

# COMMAND ----------

register_table("movie_silver", movie_silver_path)