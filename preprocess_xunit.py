#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on Aug 4, 2015

A script to preprocess xUnit Suite Results files before importing them into Polarion.
The script makes sure that the test case work items are created with a unique name by
adding the name of the project before the fully qualified class name in the file and
putting all results into a single xUnit file.

Assumptions:
   xUnit results files are named TEST-<test_suite_name>.xml
   
@param param: The path of a directory to search for xUnit results files
@return: A file named 'ResultsForPolarion.xml' in the directory passed to the script

@author: afield
'''

import ast
import fnmatch
import operator
import os
import re
import sys
import tempfile


# Dictionary that holds the total counts and times for all of the testsuites
global suite_total

# A list of properties strings
global properties

# xUnit Suite Result file name pattern
xunit_file_name_pattern = 'TEST-*.xml'

def main():

   if len( sys.argv ) != 2:
      print( "%s - Supply the path to search for xUnit suite results files" % len( sys.argv ) )
      sys.exit( 2 )
   else:
      base_dir = sys.argv[1]
      if not base_dir.endswith( os.path.sep ):
         base_dir = "%s%s" % ( base_dir, os.path.sep )

   xunit_file_paths = get_xunit_results_file_paths( base_dir )

   first_xunit_file = True
   fh, target_file_path = tempfile.mkstemp()
   with open( target_file_path, 'w' ) as target_file:
      for xunit_path in xunit_file_paths:
         print( "Processing file: '%s'" % ( xunit_path ) )

         # Get project names from file paths into projects
         # The project name is everything between base_dir and either 'target' or 'test-output'
         project_name = get_project_name( base_dir, xunit_path )

         # Read files and replace classname with project_name+_+classname
         property_strings = ['<properties>', '</properties>', '<property ']
         all_strings = property_strings + [  '<?xml ']
         with open( xunit_path, 'r' ) as source_file:
            for line in source_file:
               # Only write Java properties once
               if first_xunit_file and ( any( x in line for x in property_strings ) or line == '"/>\n' ):
                  properties.append( line )
               elif line.find( '<testcase ' ) != -1:
                  target_file.write( line.replace( 'classname="', 'classname="%s_' % ( project_name ) ) )
               elif line.find( '<testsuite ' ) != -1:
                  parse_testsuite_line( xunit_path, line )
                  # Remove timestamps, because of POLARION-648
                  target_file.write( "\n%s" % re.sub( 'timestamp=".*"', '', line ) )
               elif any( x in line for x in all_strings ) or line == '"/>\n':
                  # print( ("Skipping line: '%s' from file '%s'" % ( line, xunit_path )).replace('\n','') )
                  continue
               else:
                  target_file.write( line )
         first_xunit_file = False

   # Compile the final file
   write_final_results_file( base_dir, target_file_path )

def get_project_name( base_dir, file_path ):
   '''
   The project name is derived from the path to the xUnit results file by removing the 
   path passed to the script and everything in the path after 'target' or 'test-output'.
   '/' characters are replaced with '_' characters.
   
   For example, if the path to search is '/home/user/projects/infinispan', and the path
   to the xUnit results file is '/home/user/projects/infinispan/jcache/remote/target/surefire-reports/TEST-TestSuite.xml'
   then the project name is 'jcache_remote_'.
   
   @param base_dir: The main directory being searched
   @param file_path: The path to a specific xUnit result file
   @return: The project name
   '''
   if file_path.find( 'target' ) != -1:
      return file_path[len( base_dir ):file_path.rfind( 'target' ) - 1].replace( '/', '_' )
   elif file_path.find( 'test-output' ) != -1:
      return file_path[len( base_dir ):file_path.rfind( 'test-output' ) - 1].replace( '/', '_' )


def write_final_results_file( results_dir, testcase_file ):
   '''
   Write the xUnit result file containing all of the test cases and the global counts
   
   @param results_dir: The directory where the 'ResultsForPolarion.xml' will be written
   @param testcase_file: The file containing all of the testcase information from all of the xUnit results files
   '''
   with open( os.path.join( results_dir, 'ResultsForPolarion.xml' ), 'w' ) as results_file:
      results_file.write( '<?xml version="1.0" encoding="UTF-8"?>\n' )
      results_file.write( '<testsuites>\n' )
      results_file.write( '<testsuite name="ResultsForPolarion"  time="%s" tests="%s" errors="%s" skipped="%s" failures="%s" >\n' % ( suite_total['time'], suite_total['tests'], suite_total['errors'], suite_total['skipped'], suite_total['failures'] ) )
      for prop in properties:
         results_file.write( prop )
      with open( testcase_file, 'r' ) as testcase_file:
         for line in testcase_file:
            results_file.write( line )
      results_file.write( '</testsuite>\n' )
      results_file.write( '</testsuites>\n' )


def get_xunit_results_file_paths( search_dir ):
   '''
   Search the specified path for any xUnit results files and put them in a list
   
   @param search_dir:  The path to a directory to search for xUnit results files
   @return: A list containing paths to every xUnit result file found in the search_dir sorted from largest to smallest file size
   '''
   file_stats = {}
   # Gather all xUnit suite results files into paths
   for root, dirnames, filenames in os.walk( search_dir ):
      for filename in fnmatch.filter( filenames, xunit_file_name_pattern ):
         file_stats[os.path.join( root, filename )] = os.stat( os.path.join( root, filename ) ).st_size

   sorted_file_stats = sorted( file_stats.items(), key=operator.itemgetter( 1 ), reverse=True )

   result = []
   for stat in sorted_file_stats:
      result.append( stat[0] )

   return result

def parse_testsuite_line( file_path, line ):
   '''
   Parse the testsuite XML tag and update the global counts in the suite_total variable

   Example:
   <testsuite hostname="localhost.localdomain" name="org.infinispan.persistence.leveldb.JniLevelDBStoreFunctionalTest" tests="8" failures="0" timestamp="25 Aug 2014 13:07:12 GMT" time="1.207" errors="0">
   
   @param line:  The line from the file containing the <testsuite XML tag
   '''
   #print("line = %s" % (line))
   line_list = line.strip().replace( "<testsuite ", "" ).replace( ">", "" ).replace( "\"", "" ).split()
   for each in line_list:
      # These values are not used by the Polarion test run, so skip them
      if each.find( 'name' ) != -1 or each.find( 'hostname' ) != -1 or each.find( 'timestamp' ) != -1 or each.find( '=' ) == -1:
         continue
      else:
         new_list = each.split( '=' )
         #print( "new_list = %s" % ( new_list ) )
         suite_total[new_list[0]] += ast.literal_eval( new_list[1].replace(",","") )
   # print( "suite_total = %s" % ( suite_total ) )

if __name__ == '__main__':
   suite_total = {'time': 0, 'tests': 0, 'errors': 0, 'skipped': 0, 'failures': 0, }
   properties = []
   main()
