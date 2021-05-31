.. DESDEO documentation master file, created by
   sphinx-quickstart on Thu Jun  4 12:22:29 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to DESDEO's documentation!
==================================

Decision Support for computationally Demanding Optimization problems

DESDEO is a free and open-source Python-based framework for developing and experimenting with interactive multiobjective optimization. It contains implementations of some interactive methods and modules that can be utilized to implement further methods. 

We welcome you to utilize DESDEO and develop it further with us.



.. figure:: /images/desdeo-main.svg
   :figclass: imgcenter

For news and other information related to DESDEO, see the official website_.

Packages
========
.. role:: raw-html(raw)
   :format: html

.. only:: builder_html and (not singlehtml)

   .. container:: tocdescr

      .. container:: descr

         .. figure:: /images/desdeo_problem.png

         **desdeo-problem**
                This package contains tools and classes for defining and
		modelling multiobjective optimization problems. The defined problem classes
		can be used in the other packages in the DESDEO framework, such as
		**desdeo-mcdm** and **desdeo-emo**.

		|br|
		
		.. container:: btndoc

			`Go to documentation <https://desdeo-problem.readthedocs.io/en/latest/index.html>`__

      .. container:: descr

         .. figure:: /images/desdeo_tools.png

         **desdeo-tools** 
            	This package contains tools to facilitate different tasks in the
		other packages in the DESDEO framework. These tools include, for example,
		scalarization routines and various solvers.

		|br|

		.. container:: btndoc

			`Go to documentation <https://desdeo-tools.readthedocs.io/en/latest/index.html>`__

      .. container:: descr

         .. figure:: /images/desdeo_emo.png

         **desdeo-emo**
            	This package contains evolutionary algorithms for solving multiobjective optimization problems.
		These algorithms include, for example, interactive RVEA.

		|br|

		.. container:: btndoc

			`Go to documentation <https://desdeo-emo.readthedocs.io/en/latest/index.html>`__

      .. container:: descr

	 
	 .. figure:: /images/desdeo_mcdm.png
 
	 **desdeo-mcdm** 
            	This package contains traditional methods for performing
            	interactive multiobjective optimization. These methods include, but are not
            	limited to, Synchronous NIMBUS and E-NAUTILUS, for example.

		|br|

		.. container:: btndoc

			`Go to documentation <https://desdeo-mcdm.readthedocs.io/en/latest/index.html>`__



.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents


   introduction
   software
   guides
   contributing
   glossary

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
.. _desdeo-mcdm: https://desdeo-mcdm.readthedocs.io/en/latest/index.html
.. _desdeo-emo: https://desdeo-emo.readthedocs.io/en/latest/index.html
.. _desdeo-tools: https://desdeo-tools.readthedocs.io/en/latest/index.html
.. _desdeo-problem: https://desdeo-problem.readthedocs.io/en/latest/

.. |br| raw:: html

      <br>
