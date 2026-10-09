// Forms are generated only from a reviewed, bounded device schema; the server remains authoritative.
import { l } from "./i18n.js";

export function schemaControl(schema, ui, depth = 0, options = {}) {
  const { e, div, input, select, field, btn } = ui;
  const { blank = false, initial } = options;
  if (
    depth > 5 ||
    !schema ||
    schema.$ref ||
    schema.oneOf ||
    schema.anyOf ||
    schema.allOf ||
    schema.if
  )
    throw new Error(
      l(
        "Profile cần form riêng cho cấu trúc này.",
        "This profile requires a dedicated form for this structure.",
      ),
    );
  if (schema.const !== undefined) {
    if (initial !== undefined && JSON.stringify(initial) !== JSON.stringify(schema.const)) throw new Error(l("Giá trị đã lưu khác hồ sơ hiện tại.", "Saved value differs from the current profile."));
    return {
      node: e("span", JSON.stringify(schema.const)),
      read: () => schema.const,
    };
  }
  if (schema.enum) {
    if (initial !== undefined && !schema.enum.some(v=>JSON.stringify(v)===JSON.stringify(initial))) throw new Error(l("Giá trị đã lưu không còn trong danh sách của hồ sơ.", "Saved value is no longer listed in the profile."));
    const node = select(
      [...(blank ? [["", l("Chọn giá trị", "Choose a value")]] : []), ...schema.enum.map((v, i) => [
        String(i),
        typeof v === "object" ? JSON.stringify(v) : String(v),
      ])],
      initial === undefined ? (blank ? "" : "0") : String(schema.enum.findIndex(v => JSON.stringify(v) === JSON.stringify(initial))),
    );
    return { node, read: () => {
      if (node.value === "" || !Object.hasOwn(schema.enum, node.value)) throw new Error(l("Chọn giá trị trong danh sách.", "Choose a listed value."));
      return schema.enum[Number(node.value)];
    } };
  }
  if (schema.type === "object") {
    if (initial && Object.keys(initial).some(key => !Object.hasOwn(schema.properties || {}, key))) throw new Error(l("Có trường đã lưu chưa có định nghĩa trong hồ sơ.", "A saved field has no definition in the profile."));
    const node = div("form-grid"),
      controls = [];
    for (const [key, child] of Object.entries(schema.properties || {})) {
      const c = schemaControl(child, ui, depth + 1, {blank, initial: initial?.[key]}),
        required = (schema.required || []).includes(key),
        enabled = input("checkbox");
      enabled.checked = required || (initial != null && Object.hasOwn(initial, key));
      const container = div("stack", field(child.title || key, c.node));
      if (!required) {
        container.prepend(
          field(l("Có dùng ", "Include ") + (child.title || key), enabled),
        );
        c.node.hidden = !enabled.checked;
        enabled.onchange = () => {
          c.node.hidden = !enabled.checked;
        };
      }
      controls.push({ key, c, enabled, required });
      node.append(container);
    }
    if (
      (schema.required || []).some(
        (key) => !controls.some((c) => c.key === key),
      )
    )
      throw new Error(
        l(
          "Thiếu định nghĩa trường bắt buộc.",
          "Required field schema is missing.",
        ),
      );
    return {
      node,
      read: () =>
        Object.fromEntries(
          controls
            .filter((c) => c.required || c.enabled.checked)
            .map((c) => [c.key, c.c.read()]),
        ),
    };
  }
  if (schema.type === "array") {
    if (
      !Number.isInteger(schema.maxItems) ||
      schema.maxItems > 168 ||
      !schema.items ||
      Array.isArray(schema.items)
    )
      throw new Error(
        l(
          "Cần giới hạn số dòng đúng model.",
          "A bounded model-specific row count is required.",
        ),
      );
    const node = div("stack"),
      list = div("stack"),
      entries = [];
    const addRow = (value) => {
      if (entries.length >= schema.maxItems) return;
      const c = schemaControl(schema.items, ui, depth + 1, {blank, initial: value}),
        row = div("array-row", c.node);
      row.append(
        btn(l("Xóa dòng", "Remove row"), () => {
          if (entries.length <= (schema.minItems || 0)) return;
          entries.splice(entries.indexOf(c), 1);
          row.remove();
        }),
      );
      entries.push(c);
      list.append(row);
    };
    if (Array.isArray(initial)) {
      if (initial.length > schema.maxItems) throw new Error(l("Bản nháp vượt số dòng cho phép.", "Draft exceeds the allowed row count."));
      initial.forEach(value => addRow(value));
    }
    while (entries.length < (schema.minItems || 0)) addRow();
    node.append(list, btn(l("+ Thêm dòng", "+ Add row"), () => addRow()));
    return { node, read: () => entries.map((c) => c.read()) };
  }
  if (schema.type === "boolean") {
    if (blank) {
      const node = select([["", l("Chọn trạng thái", "Choose a state")], ["true", l("Bật", "On")], ["false", l("Tắt", "Off")]], typeof initial === 'boolean' ? String(initial) : "");
      return {node, read: () => {
        if (!['true', 'false'].includes(node.value)) throw new Error(l("Chọn bật hoặc tắt.", "Choose on or off."));
        return node.value === 'true';
      }};
    }
    const node = input("checkbox");
    node.checked = initial === true;
    return { node, read: () => node.checked };
  }
  if (["integer", "number"].includes(schema.type)) {
    if (schema.minimum == null || schema.maximum == null)
      throw new Error(
        l(
          "Cần giới hạn đã xác minh cho thông số.",
          "Verified parameter bounds are required.",
        ),
      );
    const node = input("number", initial ?? (blank ? "" : schema.default ?? schema.minimum));
    node.min = schema.minimum;
    node.max = schema.maximum;
    node.step = schema.multipleOf || (schema.type === "integer" ? 1 : "any");
    return {
      node,
      read: () => {
        if (node.value === "" || !node.checkValidity())
          throw new Error(
            l(
              "Kiểm tra giá trị và giới hạn.",
              "Check the value and its limits.",
            ),
          );
        return Number(node.value);
      },
    };
  }
  if (schema.type === "string") {
    const node = input("text", initial ?? (blank ? "" : schema.default || ""));
    node.maxLength = schema.maxLength || 256;
    node.minLength = schema.minLength || 0;
    if (schema.pattern) node.pattern = schema.pattern;
    return {
      node,
      read: () => {
        if (!node.checkValidity())
          throw new Error(
            l("Thông số không đúng định dạng.", "Parameter format is invalid."),
          );
        return node.value;
      },
    };
  }
  throw new Error(
    l(
      "Kiểu thông số chưa có form được hỗ trợ.",
      "No supported form for this parameter type.",
    ),
  );
}
