# Databricks notebook source
from typing import *
from delta.tables import DeltaTable
from pyspark.sql import DataFrame, DataFrameWriter, SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.sql.window import *

# COMMAND ----------

def move_raw(old_path: str, new_path: str) -> bool:
  file_list = [[file.path, file.name] for file in dbutils.fs.ls(old_path) if file.name.startswith("movie")]
  
  for file in file_list:
    dbutils.fs.cp(file[0], new_path + "/" +file[1])
  
  return True

# COMMAND ----------

def read_raw(path: str, schema: StructType) -> DataFrame:
  return (spark.read
                .option("multiLine", "true")
                .schema(schema)
                .json(path))

# COMMAND ----------

def add_metadata(raw: DataFrame) -> DataFrame:
  return (raw.withColumn("datasource", lit("trainning"))
             .withColumn("ingesttime", current_timestamp())
             .withColumn("status", lit("new"))
             .withColumn("ingestdate", current_timestamp().cast("date")))
  

# COMMAND ----------

def write_delta(
    dataframe: DataFrame,
    exclude_columns: List = [],
    mode: str = "append"
) -> DataFrameWriter:
    return (
        dataframe.drop(
            *exclude_columns
        )
        .write.format("delta")
        .mode(mode)
    )

# COMMAND ----------

def register_table(table: str, path: str) -> None:
  spark.sql(f"""
  DROP TABLE IF EXISTS {table}
  """)

  spark.sql(f"""
  CREATE TABLE {table}
  USING DELTA
  LOCATION "{path}"
  """)
  
  return True

# COMMAND ----------

def read_table(table: str) -> DataFrame:
  return spark.read.table(table)

# COMMAND ----------

def explode_bronze(bronze: DataFrame, explode_column: str, alias: str, column: List = []) -> DataFrame:
  if column:
    return bronze.select(*column, explode(col(explode_column)).alias(alias))
  else:
    return bronze.select(explode(col(explode_column)).alias(alias))

# COMMAND ----------

def transform_bronze(bronze: DataFrame, column: str) -> DataFrame:
  return bronze.select(col(column), 
                      col(column + ".*"))

# COMMAND ----------

# def filter_null(bronze: DataFrame, column: str) -> (DataFrame, DataFrame):
#   return (bronze.filter(col(column) == ''),
#          bronze.filter(col(column) != ''))

# COMMAND ----------

def filter_less_than(bronze: DataFrame, column: str, threshold: int) -> (DataFrame, DataFrame):
  return (bronze.filter(col(column) < threshold),
         bronze.filter(col(column) >= threshold))

# COMMAND ----------

##### Old-version update status function cant handle duplicate values
# def update_bronze_status(spark: SparkSession, path: str, dataframe: DataFrame, matchvalue: str, status: str) -> bool:
#   bronze_delta_table = DeltaTable.forPath(spark, path)
#   dataframe_new_status = dataframe.withColumn("status", lit(status))
  
#   update_match = f"dataframe.{matchvalue} = bronze.{matchvalue}"
#   update = {"status" : "dataframe.status"}
  
#   (
#     bronze_delta_table.alias("bronze")
#     .merge(dataframe_new_status.alias("dataframe"), update_match)
#     .whenMatchedUpdate(set = update)
#     .execute()
#   )
  
#   return True

# COMMAND ----------

def update_bronze_status(path: str, status: str, view: DataFrame, condition: str = "IN") -> bool:
  spark.sql(f"""
    UPDATE delta.`{path}` 
    SET status = '{status}' 
    WHERE value {condition} (SELECT value FROM {view})
  """)
  return True

# COMMAND ----------

def get_quarantined_df(bronze_table: str) -> DataFrame:
    quarantined_df = spark.read.table(bronze_table).filter(col("status") == 'quarantined')
    transformed_quarantined_df = transform_bronze(quarantined_df, "value")
    
    return transformed_quarantined_df


# COMMAND ----------

def drop_genres_replace_language(dataframe: DataFrame) -> DataFrame:
  language = spark.read.table("language_silver")
  
  return (dataframe
          .join(language, dataframe.OriginalLanguage == language.language)
          .select(*dataframe.columns, "languageid")
          .withColumn('OriginalLanguage', col("languageid"))
          .drop("languageid", "genres"))

# COMMAND ----------

