.. _api-model:

.. currentmodule:: sdmx.model

.. module:: sdmx.model

SDMX Information Model
**********************

See the :ref:`implementation notes <im>`.

Quick links to classes common to SDMX 2.1 and 3.0 (in alphabetical order):

.. include:: model-common-list.rst

Quick links to classes specific to the SDMX 2.1 implementation:

.. include:: model-v21-list.rst

Quick links to classes specific to the SDMX 3.0 implementation:

.. include:: model-v30-list.rst


Common to SDMX 2.1 and 3.0
--------------------------

.. automodule:: sdmx.model.internationalstring
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: sdmx.model.common
   :members:
   :ignore-module-all:
   :exclude-members: InternationalString, SDMXtoVTL, VTLtoSDMX
   :undoc-members:
   :show-inheritance:

.. currentmodule:: sdmx.model.v21

SDMX 2.1
--------

.. automodule:: sdmx.model.v21
   :members:
   :ignore-module-all:
   :undoc-members:
   :show-inheritance:

   .. autoclass:: KeyValue
      :members:
      :special-members: __eq__


.. currentmodule:: sdmx.model.v30

SDMX 3.0
--------

.. automodule:: sdmx.model.v30
   :members:
   :ignore-module-all:
   :undoc-members:
   :show-inheritance:

   .. autoclass:: KeyValue
      :members:
      :special-members: __eq__
