'''
Created on June 15, 2016

@author: afield


>>> import sys
>>> sys.path.append('/Users/afield/Development/projects/polarion-preprocess')
>>> from polarion_mapping import PolarionMapping
>>> d = PolarionMapping()

>>> d['invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.StringBasedCacheStoreCFPooledIT.testPutGetRemoveWithPassivationWithoutPreload']
JDG-98

>>> d.sync(True)
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.MixedCacheStoreIT.testPutGetRemoveWithPassivationWithoutPreload' with ID 'JDG-102'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.StringBasedCacheStoreCFPooledIT.testPutGetRemoveWithoutPassivationWithPreload' with ID 'JDG-97'
Adding 'invm_async-cache-store_com.jboss.datagrid.test.asyncstore.AsyncFileCacheStoreWithEvictionIT.testPutRemove' with ID 'JDG-103'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.StringBasedCacheStoreCFManagedIT.testPutGetRemoveWithPassivationWithoutPreload' with ID 'JDG-96'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.BinaryCacheStoreIT.testPutGetRemoveWithoutPassivationWithPreload' with ID 'JDG-99'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.StringBasedCacheStoreCFPooledIT.testPutGetRemoveWithPassivationWithoutPreload' with ID 'JDG-98'
Adding 'invm_async-cache-store_com.jboss.datagrid.test.asyncstore.AsyncFileCacheStoreWithoutEvictionIT.testPutRemove' with ID 'JDG-93'
Adding 'invm_async-cache-store_com.jboss.datagrid.test.asyncstore.AsyncFileCacheStoreWithoutEvictionIT.testPutClearPut' with ID 'JDG-92'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.BinaryCacheStoreIT.testPutGetRemoveWithPassivationWithoutPreload' with ID 'JDG-100'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.StringBasedCacheStoreCFManagedIT.testPutGetRemoveWithoutPassivationWithPreload' with ID 'JDG-95'
Adding 'invm_async-cache-store_com.jboss.datagrid.test.asyncstore.AsyncFileCacheStoreWithoutEvictionIT.testMultiplePutsOnSameKey' with ID 'JDG-94'
Adding 'invm_jdbc-cache-store_com.jboss.datagrid.test.jdbcstore.MixedCacheStoreIT.testPutGetRemoveWithoutPassivationWithPreload' with ID 'JDG-101'

This class implements a persistent mapping from testCaseID to workItemID that can be used for adding Polarion IDs
to XUnit results files. It depends upon Pylarion.
'''
import collections
import shelve
from pylarion.work_item import TestCase 

class PolarionMapping(collections.MutableMapping):
   lucene_special_chars = ['+', '-', '&&', '||', '!', '(', ')', '{', '}', '[', ']', '^', '\"', '~', '*', '?', ':', '\\']
   
   def __init__(self, project_name=None, *args, **kwargs):
      if project_name == None:
         self.polarion = TestCase()
         self.project_name = self.polarion.default_project
      else:
         self.project_name = project_name
      # Open a persistent shelf for the default or specified project
      self.shelf = shelve.open(self.project_name)

   def __del__(self):
      # Closing the shelf flushes and saves it
      self.shelf.close()

   def __getitem__(self, key):
      if self.shelf.has_key(key):
         return self.shelf.__getitem__(key)
      else:
         # Query Polarion for the test case if it isn't in the shelf
         tests = self.polarion.query("testCaseID:%s OR title:%s" % (self.escape_query(key), self.escape_query(key)), fields=["work_item_id", "title"], project_id=self.project_name)
         if len(tests) == 0:
            print "Test case '%s' does not exist in Polarion" % key
            return None
         elif len(tests) == 1:
            self.shelf[str(key)] = str(tests[0].work_item_id)
            return self.shelf.__getitem__(key)
         else:
            err_str = "Found multiple test cases with testCaseID '%s' in Polarion\n" % key
            for tc in tests:
               if tc.test_case_id is not None:
                  err_str += "testCaseID: '%s'; workItemID: '%s'\n" % (tc.test_case_id, tc.work_item_id)
               elif tc.title is not None:
                  err_str += "title: '%s'; workItemID: '%s'\n" % (tc.title, tc.work_item_id)
            raise RuntimeError(err_str)

   def __setitem__(self, key, val):
      self.shelf[str(key)] = str(val)
      
   def __delitem__(self, key):
      self.shelf.pop(key, None)
   
   def __iter__(self):
      return self.shelf.__iter__()
   
   def __len__(self):
      return len(self.shelf)

   def __repr__(self):
      return self.shelf.__repr__()

   def escape_query(self, query_str):
      '''Escape Lucene Query Syntax Special Characters'''
      for char in self.lucene_special_chars:
         escape_str = query_str.replace(char, '\%s' % char)
      return escape_str

   def sync(self, full=False):
      '''Sync the mapping with Polarion. If full is True, then do a complete re-sync.'''
      tests = self.polarion.query("", fields=["work_item_id", "title"], project_id=self.project_name)
      if full:
         self.shelf.clear()
      for test in tests:
         if test.test_case_id is not None and not self.shelf.has_key(str(test.test_case_id)):
            print "Adding '%s' with ID '%s'" % (test.test_case_id, test.work_item_id)
            self.shelf[str(test.test_case_id)] = str(test.work_item_id)
         elif test.title is not None and not self.shelf.has_key(str(test.title)):
            print "Adding '%s' with ID '%s'" % (test.title, test.work_item_id)
            self.shelf[str(test.title)] = str(test.work_item_id)
            