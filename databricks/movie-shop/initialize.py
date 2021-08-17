# Databricks notebook source
spark.sql("DROP DATABASE IF EXISTS movieshop CASCADE")

# COMMAND ----------

dbutils.fs.rm("/movieshop", True)

# COMMAND ----------

