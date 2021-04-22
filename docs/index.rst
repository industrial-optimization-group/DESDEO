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
            :target: https://desdeo-problem-test.readthedocs.io/en/latest/index.html

         desdeo-problem_
                The **desdeo-problem** package contains tools and classes for defining and
		modelling multiobjective optimization problems. The defined problem classes
		can be used in the other packages in the DESDEO framework, such as
		**desdeo-mcdm** and **desdeo-emo**.

      .. container:: descr

         .. figure:: /images/desdeo_tools.png
            :target: https://desdeo-tools-test.readthedocs.io/en/latest/index.html

         desdeo-tools_
            	The **desdeo-tools** package contains tools to facilitate different tasks in the
		other packages in the DESDEO framework. These tools include, for example,
		scalarization routines and various solvers.

      .. container:: descr

         .. figure:: /images/desdeo_emo.png
            :target: https://desdeo-emo-test.readthedocs.io/en/latest/index.html

         desdeo-emo_
            	The **desdeo-emo** package contains evolutionary algorithms for solving multiobjective optimization problems.
		These algorithms include, for example, interactive RVEA.

      .. container:: descr

         .. figure:: /images/desdeo_mcdm.png
            :target: https://desdeo-mcdm-test.readthedocs.io/en/latest/index.html


	 desdeo-mcdm_
            	The **desdeo-mcdm** package contains traditional methods for performing
		interactive multiobjective optimization. These methods include, but are not
		limited to, Synchronous NIMBUS and E-NAUTILUS, for example.



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

   desdeo-mcdm <https://desdeo-mcdm-test.readthedocs.io/en/latest/>

   desdeo-emo <https://desdeo-emo-test.readthedocs.io/en/latest/>

   desdeo-problem <https://desdeo-problem-test.readthedocs.io/en/latest/>

   desdeo-tools <https://desdeo-tools-test.readthedocs.io/en/latest>

   DESDEO website <https://desdeo.it.jyu.fi>

.. _website: https://desdeo.it.jyu.fi
.. _desdeo-mcdm: https://desdeo-mcdm-test.readthedocs.io/en/latest/index.html
.. _desdeo-emo: https://desdeo-emo-test.readthedocs.io/en/latest/index.html
.. _desdeo-tools: https://desdeo-tools-test.readthedocs.io/en/latest/index.html
.. _desdeo-problem: https://desdeo-problem-test.readthedocs.io/en/latest/
