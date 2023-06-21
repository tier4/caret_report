var cy = (window.cy = cytoscape({
  container: document.getElementById("cy"),

  style: [
    {
      selector: "node",
      style: {
        label: "data(text)",
        "font-size": "10",
        "text-wrap": "wrap",
        width: "20",
        height: "20",
      },
    },
    {
      selector: ":parent",
      style: {
        label: "",
        shape: "round-rectangle",
      },
    },
    {
      selector: ".result",
      style: {
        "text-valign": "center",
        "text-halign": "right",
      },
    },
    {
      selector: ".external",
      style: {
        "text-valign": "top",
        "text-halign": "center",
        shape: "round-rectangle",
        width: "10",
        height: "10",
        "background-color": "#333",
        visibility: "hidden",
      },
    },
    {
      selector: "edge",
      style: {
        "source-label": "data(text)",
        "source-text-offset": 25,
        // "source-text-margin-y": 10,
        "font-size": "10",
        "curve-style": "bezier",
        "target-arrow-shape": "triangle",
        "text-background-color": "#FFF",
        "text-background-opacity": "0.8",
      },
    },
    {
      selector: ".pass",
      style: {
        "background-color": "#0F0",
        "line-color": "#0F0",
        "target-arrow-color": "#0F0",
      },
    },
    {
      selector: ".failed",
      style: {
        "background-color": "#F00",
        "line-color": "#F00",
        "target-arrow-color": "#F00",
      },
    },
    {
      selector: ".not_measured",
      style: {
        "background-color": "#FF0",
        "line-color": "#EE0",
        "target-arrow-color": "#EE0",
      },
    },
  ],

  elements: {
    nodes: [
      { data: { id: "sensing_box" } },
      { data: { id: "localization_box" } },
      { data: { id: "perception_box" } },
      { data: { id: "planning_box" } },
      { data: { id: "control_box" } },
      { data: { id: "vehicle_box" } },
      { data: { id: "system_box" } },

      { data: { id: "sensing", parent: "sensing_box", text: "sensing\n0/0" }, classes: "result" },
      {
        data: { id: "localization", parent: "localization_box", text: "localization\n0/0" },
        classes: "result",
      },
      {
        data: { id: "perception", parent: "perception_box", text: "perception\n0/0" },
        classes: "result",
      },
      {
        data: { id: "planning", parent: "planning_box", text: "planning\n0/0" },
        classes: "result",
      },
      { data: { id: "control", parent: "control_box", text: "control\n0/0" }, classes: "result" },
      { data: { id: "vehicle", parent: "vehicle_box", text: "vehicle\n0/0" }, classes: "result" },
      { data: { id: "system", parent: "system_box", text: "system\n0/0" }, classes: "result" },

      { data: { id: "sensing_ext", text: "External" }, classes: "external" },

      { data: { id: "localization_ext", text: "External" }, classes: "external" },

      { data: { id: "perception_ext", text: "External" }, classes: "external" },

      { data: { id: "planning_ext", text: "External" }, classes: "external" },

      { data: { id: "control_ext", text: "External" }, classes: "external" },

      { data: { id: "vehicle_ext", text: "External" }, classes: "external" },

      { data: { id: "system_ext", text: "External" }, classes: "external" },
    ],

    edges: [
      // { data: { id: "sensing_ext", source: "sensing_ext", target: "sensing_box", text: "10/20" } },
    ],
  },

  // layout: {
  //   name: "preset",
  //   padding: 5,
  // },
  // zoom: 2,
  // pan: { x: 300, y: 600 },
}));

cy.getElementById("sensing").position({ x: -50, y: 0 });
cy.getElementById("localization").position({ x: 0, y: 100 });
cy.getElementById("perception").position({ x: 200, y: 100 });
cy.getElementById("planning").position({ x: 250, y: 0 });
cy.getElementById("control").position({ x: 250, y: -100 });
cy.getElementById("vehicle").position({ x: 50, y: -100 });
cy.getElementById("system").position({ x: 150, y: -170 });

cy.getElementById("sensing_ext").position(
  "x",
  cy.getElementById("sensing_box").position("x") - 100,
);
cy.getElementById("sensing_ext").position("y", cy.getElementById("sensing_box").position("y"));
cy.getElementById("localization_ext").position(
  "x",
  cy.getElementById("localization_box").position("x") - 100,
);
cy.getElementById("localization_ext").position(
  "y",
  cy.getElementById("localization_box").position("y"),
);
cy.getElementById("perception_ext").position(
  "x",
  cy.getElementById("perception_box").position("x") + 100,
);
cy.getElementById("perception_ext").position(
  "y",
  cy.getElementById("perception_box").position("y"),
);
cy.getElementById("planning_ext").position(
  "x",
  cy.getElementById("planning_box").position("x") + 100,
);
cy.getElementById("planning_ext").position("y", cy.getElementById("planning_box").position("y"));
cy.getElementById("control_ext").position(
  "x",
  cy.getElementById("control_box").position("x") + 100,
);
cy.getElementById("control_ext").position("y", cy.getElementById("control_box").position("y"));
cy.getElementById("vehicle_ext").position(
  "x",
  cy.getElementById("vehicle_box").position("x") - 100,
);
cy.getElementById("vehicle_ext").position("y", cy.getElementById("vehicle_box").position("y"));
cy.getElementById("system_ext").position("x", cy.getElementById("system_box").position("x") - 100);
cy.getElementById("system_ext").position("y", cy.getElementById("system_box").position("y"));

cy.fit();
cy.zoomingEnabled(false);
cy.panningEnabled(false);
cy.boxSelectionEnabled(false);
cy.nodes().lock();
cy.nodes().unselectify();
cy.edges().lock();
cy.edges().unselectify();

// Update using callback validation result
let metrics = "FREQUENCY";
for (let component_name in summary_callback_dict_component_metrics) {
  let cnt_pass = summary_callback_dict_component_metrics[component_name][metrics].cnt_pass;
  let cnt_failed = summary_callback_dict_component_metrics[component_name][metrics].cnt_failed;
  let cnt_not_measured =
    summary_callback_dict_component_metrics[component_name][metrics].cnt_not_measured;
  let cnt_total = cnt_pass + cnt_failed;
  let class_name = "pass";
  if (cnt_not_measured > 0) {
    class_name = "not_measured";
  }
  if (cnt_failed > 0) {
    class_name = "failed";
  }
  cy.getElementById(component_name).data(
    "text",
    component_name + "\n" + cnt_pass + " / " + cnt_total,
  );
  cy.getElementById(component_name).addClass(class_name);
  html = "validate_callback/" + component_name + "/index.html";
  cy.getElementById(component_name).data("html", html);
  cy.getElementById(component_name + "_box").data("html", html);
}

cy.on("tap", "node", function (evt) {
  let node = evt.target;
  let html = node.data("html");
  if (html != null) {
    window.open(html, "_blank");
  }
});

// Update using topic validation result
for (let componentpair in summary_topic_dict_component_pair_metrics) {
  let pub_component_name = componentpair.split("-")[0];
  let sub_component_name = componentpair.split("-")[1];
  let cnt_pass = summary_topic_dict_component_pair_metrics[componentpair][metrics].cnt_pass;
  let cnt_failed = summary_topic_dict_component_pair_metrics[componentpair][metrics].cnt_failed;
  let cnt_not_measured =
    summary_topic_dict_component_pair_metrics[componentpair][metrics].cnt_not_measured;
  let cnt_total = cnt_pass + cnt_failed;
  let class_name = "pass";
  if (cnt_not_measured > 0) {
    class_name = "not_measured";
  }
  if (cnt_failed > 0) {
    class_name = "failed";
  }

  if (pub_component_name != "external" && sub_component_name != "external") {
    cy.add({
      group: "edges",
      data: {
        id: componentpair,
        source: pub_component_name + "_box",
        target: sub_component_name + "_box",
        text: cnt_pass + " / " + cnt_total,
      },
    });
    // if (pub_component_name == "localization") {
    //   cy.getElementById(componentpair).style("source-text-offset", 100);
    // }
  } else if (pub_component_name == "external" && sub_component_name != "external") {
    ext = sub_component_name + "_ext";
    cy.getElementById(ext).style("visibility", "visible");
    cy.add({
      group: "edges",
      data: {
        id: componentpair,
        source: ext,
        target: sub_component_name + "_box",
        text: cnt_pass + " / " + cnt_total,
      },
    });
  } else if (pub_component_name != "external" && sub_component_name == "external") {
    ext = pub_component_name + "_ext";
    cy.getElementById(ext).style("visibility", "visible");
    cy.add({
      group: "edges",
      data: {
        id: componentpair,
        source: pub_component_name + "_box",
        target: ext,
        text: cnt_pass + " / " + cnt_total,
      },
    });
  }

  cy.getElementById(componentpair).addClass(class_name);
  html = "validate_topic/" + componentpair + "/index.html";
  cy.getElementById(componentpair).data("html", html);
}

cy.on("tap", "edge", function (evt) {
  var edge = evt.target;
  let html = edge.data("html");
  window.open(html, "_blank");
});
