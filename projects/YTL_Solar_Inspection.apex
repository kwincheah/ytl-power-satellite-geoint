<?xml version='1.0' encoding='utf-8'?>
<ApexSolution version="4.3" name="YTL_Solar_Inspection" active_flow="YTL_Campus_Solar_Flow" trigger_flow="YTL_Campus_Solar_Flow">
  <GlobalVariables>
    <Variable name="g_CampusName" type="str">YTL Green Data Center Park, Kulai</Variable>
    <Variable name="g_TargetSolarMW" type="float">100.0</Variable>
  </GlobalVariables>
  <Flows>
    <ApexFlow version="4.3" name="YTL_Campus_Solar_Flow">
      <Properties>
        <Property name="enabled" type="bool">true</Property>
        <Property name="run_interval_ms" type="float">100.0</Property>
        <Property name="stop_on_ng" type="bool">false</Property>
        <Property name="flow_timeout_ms" type="float">5000.0</Property>
        <Property name="execution_count" type="int">0</Property>
      </Properties>
      <Nodes>
        <Node instance_id="sat_src" tool_name="Satellite STAC Source" name="01_SatelliteIngest" category="Earth Observation" enabled="true">
          <Parameters>
            <Parameter name="epoch" type="str">2026-08 (Operational)</Parameter>
            <Parameter name="collection" type="str">Sentinel-2 L2A (Optical)</Parameter>
            <Parameter name="max_cloud" type="float">20.0</Parameter>
          </Parameters>
        </Node>
        <Node instance_id="spec_flt" tool_name="Spectral Index &amp; HSV Filter" name="02_SolarSpectralFilter" category="Earth Observation" enabled="true">
          <Parameters>
            <Parameter name="target_feature" type="str">Solar Photovoltaic Arrays</Parameter>
            <Parameter name="brightness_ceiling" type="int">95</Parameter>
            <Parameter name="saturation_ceiling" type="int">180</Parameter>
            <Parameter name="min_reflectance" type="int">175</Parameter>
          </Parameters>
        </Node>
        <Node instance_id="geo_msr" tool_name="Geospatial Area &amp; Capacity Estimator" name="03_PhysicalCapacityEstimator" category="Earth Observation" enabled="true">
          <Parameters>
            <Parameter name="feature_type" type="str">Solar Farm Ground Mount</Parameter>
            <Parameter name="gsd_resolution_m" type="float">10.0</Parameter>
            <Parameter name="solar_mw_per_ha" type="float">1.0</Parameter>
            <Parameter name="min_cluster_pixels" type="int">200</Parameter>
          </Parameters>
        </Node>
        <Node instance_id="cons_brn" tool_name="Consensus Variance &amp; Delivery Branch" name="04_ConsensusPacingCheck" category="Earth Observation" enabled="true">
          <Parameters>
            <Parameter name="target_mw" type="float">100.0</Parameter>
            <Parameter name="construction_pacing_rate" type="float">0.12</Parameter>
          </Parameters>
        </Node>
      </Nodes>
      <Connections>
        <Connection from_node="sat_src" from_port="Image" to_node="spec_flt" to_port="Image" />
        <Connection from_node="sat_src" from_port="Image" to_node="geo_msr" to_port="Image" />
        <Connection from_node="spec_flt" from_port="Mask" to_node="geo_msr" to_port="Mask" />
        <Connection from_node="geo_msr" from_port="Capacity_MW" to_node="cons_brn" to_port="Capacity_MW" />
      </Connections>
    </ApexFlow>
  </Flows>
</ApexSolution>
