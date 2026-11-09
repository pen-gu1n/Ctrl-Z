# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_crane_x7_gazebo_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED crane_x7_gazebo_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(crane_x7_gazebo_FOUND FALSE)
  elseif(NOT crane_x7_gazebo_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(crane_x7_gazebo_FOUND FALSE)
  endif()
  return()
endif()
set(_crane_x7_gazebo_CONFIG_INCLUDED TRUE)

# output package information
if(NOT crane_x7_gazebo_FIND_QUIETLY)
  message(STATUS "Found crane_x7_gazebo: 5.0.0 (${crane_x7_gazebo_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'crane_x7_gazebo' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT crane_x7_gazebo_DEPRECATED_QUIET)
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(crane_x7_gazebo_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${crane_x7_gazebo_DIR}/${_extra}")
endforeach()
