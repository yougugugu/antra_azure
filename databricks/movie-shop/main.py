# Databricks notebook source
# MAGIC %md
# MAGIC # initialize all

# COMMAND ----------

# MAGIC %md
# MAGIC ### movie files should be uploaded into DBFS

# COMMAND ----------

# MAGIC %run ./initialize

# COMMAND ----------

# MAGIC %run ./configuration

# COMMAND ----------

# MAGIC %run ./functions

# COMMAND ----------

# MAGIC %md
# MAGIC # raw to bronze

# COMMAND ----------

# MAGIC %md
# MAGIC ### move files

# COMMAND ----------

move_raw(upload_path, raw_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ### create schema

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

# MAGIC %md
# MAGIC ### read raw data, write and register bronze table

# COMMAND ----------

movie_raw = read_raw(raw_path, schema)
movie_explode = explode_bronze(movie_raw, "movie", "value")
movie_bronze = add_metadata(movie_explode)
write_delta(movie_bronze).partitionBy("ingestdate").save(movie_bronze_path)
register_table("movie_bronze", movie_bronze_path)

# COMMAND ----------

movie_bronze_df = read_table("movie_bronze")
transformed_bronze_df = transform_bronze(movie_bronze_df, 'value')

# COMMAND ----------

# movie_explode.count()

# COMMAND ----------

# MAGIC %md
# MAGIC ### remove raw files

# COMMAND ----------

dbutils.fs.rm(raw_path, True)

# COMMAND ----------

# MAGIC %md
# MAGIC # genre silver

# COMMAND ----------

# MAGIC %md
# MAGIC ### explode genres

# COMMAND ----------

genre_df = (explode_bronze(transformed_bronze_df, "genres", "genres")
           .distinct())
genre_df = transform_bronze(genre_df, 'genres')

# COMMAND ----------

# MAGIC %md
# MAGIC ### remove null name

# COMMAND ----------

new_genre_df = (genre_df.filter(col("name") != ''))

# COMMAND ----------

# new_genre_df.display()

# COMMAND ----------

# MAGIC %md
# MAGIC ### write and register genre into silver

# COMMAND ----------

write_delta(new_genre_df, ["genres"]).save(genre_silver_path)
register_table("genre_silver", genre_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC # movie genre silver

# COMMAND ----------

# MAGIC %md
# MAGIC ### explode genres with id

# COMMAND ----------

movie_genre_df = explode_bronze(transformed_bronze_df, "genres", "genres", ["Id"])

# COMMAND ----------

# MAGIC %md
# MAGIC ### add primary key

# COMMAND ----------

movie_genre_df = movie_genre_df.select(row_number().over(Window.orderBy(col("id"))).alias("moviegenreid"),
                                      col("id").alias("movieid"),
                                      col("genres.id").alias("genreid"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### write and register movie genre into silver 

# COMMAND ----------

write_delta(movie_genre_df).save(movie_genre_silver_path)
register_table("movie_genre_silver", movie_genre_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC # language silver

# COMMAND ----------

# MAGIC %md
# MAGIC ### read language and add primary key

# COMMAND ----------

language_df = (transformed_bronze_df.select(col("OriginalLanguage").alias("language"))
            .distinct()
            .select(row_number().over(Window.orderBy(col("language"))).alias("languageid"),
                  col("language")))

# COMMAND ----------

# MAGIC %md
# MAGIC ### write and register movie genre into silver 

# COMMAND ----------

write_delta(language_df).save(language_silver_path)
register_table("language_silver", language_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC # handle dirty data

# COMMAND ----------

# MAGIC %md
# MAGIC ### split clean data

# COMMAND ----------

semi_clean_movie_df = filter_less_than(transformed_bronze_df, "Budget", 1000000)[1]
clean_movie_df = filter_less_than(semi_clean_movie_df, "RunTime", 0)[1]

# COMMAND ----------

# MAGIC %md
# MAGIC ### write and register clean movie into silver

# COMMAND ----------

clean_movie_df = drop_genres_replace_language(clean_movie_df)
write_delta(clean_movie_df, ["value"], "overwrite").save(movie_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ### update data stauts

# COMMAND ----------

clean_movie_df.createOrReplaceTempView("clean_movie")
update_bronze_status(movie_bronze_path, "loaded", "clean_movie")
update_bronze_status(movie_bronze_path, "quarantined", "clean_movie", "NOT IN")

# COMMAND ----------

# MAGIC %md
# MAGIC ### read quarantined data

# COMMAND ----------

dirty_movie_df = get_quarantined_df("movie_bronze")

# COMMAND ----------

# MAGIC %md
# MAGIC ### repair dirty data

# COMMAND ----------

budget_clean_movie_df = filter_less_than(dirty_movie_df, "Budget", 1000000)[1]
budget_dirty_movie_df = filter_less_than(dirty_movie_df, "Budget", 1000000)[0]
repair_movie_df1 = budget_clean_movie_df.withColumn("RunTime", abs(col("RunTime")))
repair_movie_df1 = drop_genres_replace_language(repair_movie_df1)
repair_movie_df2 = (budget_dirty_movie_df.withColumn("RunTime", abs(col("RunTime")))
                                          .withColumn("Budget", lit(1000000).cast("Double")))
repair_movie_df2 = drop_genres_replace_language(repair_movie_df2)

# COMMAND ----------

# MAGIC %md
# MAGIC ### wirte repair data into silver and update repair data status

# COMMAND ----------

write_delta(repair_movie_df1, ["value"]).save(movie_silver_path)
write_delta(repair_movie_df2, ["value"]).save(movie_silver_path)
register_table("movie_silver", movie_silver_path)
repair_movie_df1.createOrReplaceTempView("repair_movie1")
update_bronze_status(movie_bronze_path, "loaded", "repair_movie1")
repair_movie_df2.createOrReplaceTempView("repair_movie2")
update_bronze_status(movie_bronze_path, "loaded", "repair_movie2")

# COMMAND ----------

# MAGIC %md
# MAGIC # handle duplicate values

# COMMAND ----------

# MAGIC %md
# MAGIC ### filter duplicate values

# COMMAND ----------

duplicate_dirty_movie_df = movie_bronze_df.groupBy(col("value")).count().filter(col("count") > 1)

# COMMAND ----------

# MAGIC %md
# MAGIC ### update dirty data status

# COMMAND ----------

duplicate_dirty_movie_df.createOrReplaceTempView("duplicate_dirty_movie")
update_bronze_status(movie_bronze_path, "quarantined", "duplicate_dirty_movie")

# COMMAND ----------

# MAGIC %md
# MAGIC ### remove duplicate values and rewrite back into silver

# COMMAND ----------

silver_movie_df = read_table("movie_silver")
silver_movie_df = silver_movie_df.distinct()
write_delta(silver_movie_df, mode = "overwrite").save(movie_silver_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ### write repair data status

# COMMAND ----------

update_bronze_status(movie_bronze_path, "loaded", "duplicate_dirty_movie")