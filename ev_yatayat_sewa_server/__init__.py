# Use PyMySQL as the MySQL driver for Django
import pymysql
pymysql.install_as_MySQLdb()
# Django 6+ requires "mysqlclient 2.2.1+"; satisfy version check when using PyMySQL
pymysql.version_info = (2, 2, 1, "final", 0)
