.. DESDEO documentation master file, created by
   sphinx-quickstart on Thu Jun  4 12:22:29 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to DESDEO's documentation!
==================================

For news and other information related to DESDEO, see the official website_.


Packages
========

.. only:: builder_html and (not singlehtml)

   .. container:: tocdescr

      .. container:: descr

         .. figure:: /images/desdeo_problem.png
            :target: interface/index.html

         :doc:`/interface/index`
                The desdeo_problem_ package contains tools and classes for defining and
		modelling multiobjective optimization problems. The defined problem classes
		can be used in the other packages in the DESDEO framework, such as
		desdeo_mcdm_ and desdeo-emo_.

      .. container:: descr

         .. figure:: /images/desdeo_tools.png
            :target: editors/index.html

         :doc:`/editors/index`
            	The desdeo_tools_ package contains tools to facilitate different tasks in the
		other packages in the DESDEO framework. These tools include, for example,
		scalarization routines and various solvers.

      .. container:: descr

         .. figure:: /images/desdeo_emo.png
            :target: scene_layout/index.html

         :doc:`/scene_layout/index`
            	The desdeo_emo_ package contains evolutionary algorithms for solving multiobjective optimization problems.
		These algorithms include, for example, interactive RVEA_.

      .. container:: descr

         .. figure:: /images/desdeo_mcdm.png
            :target: desdeo-mcdm

         desdeo-emo <https://desdeo-emo.readthedocs.io/en/latest/>
            	The desdeo_mcdm_ package contains traditional methods for performing
		interactive multiobjective optimization. These methods include, but are not
		limited to, Synchronous NIMBUS_ and E-NAUTILUS_, for example.



.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents


   introduction
   software
   guides
   contributing

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: External links

   desdeo-mcdm <https://desdeo-mcdm.readthedocs.io/en/latest/>

   desdeo-emo <https://desdeo-emo.readthedocs.io/en/latest/>

   desdeo-problem <https://desdeo-problem.readthedocs.io/en/latest/>

   desdeo-tools <https://desdeo-tools.readthedocs.io/en/latest>

   DESDEO website <https://desdeo.it.jyu.fi>

.. _website: https://desdeo.it.jyu.fi
