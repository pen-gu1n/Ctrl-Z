#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "rt_manipulators_cpp::rt_manipulators_cpp" for configuration ""
set_property(TARGET rt_manipulators_cpp::rt_manipulators_cpp APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rt_manipulators_cpp::rt_manipulators_cpp PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/librt_manipulators_cpp.so"
  IMPORTED_SONAME_NOCONFIG "librt_manipulators_cpp.so"
  )

list(APPEND _cmake_import_check_targets rt_manipulators_cpp::rt_manipulators_cpp )
list(APPEND _cmake_import_check_files_for_rt_manipulators_cpp::rt_manipulators_cpp "${_IMPORT_PREFIX}/lib/librt_manipulators_cpp.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
