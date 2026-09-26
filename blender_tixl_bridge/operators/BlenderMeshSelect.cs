#nullable enable
using System;
using System.Collections.Generic;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Interfaces;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>Exposes one animated glTF primitive to TiXL's native mesh operators.</summary>
[Guid("a8524651-56c7-58fb-94b2-cf9692f95208")]
public sealed class BlenderMeshSelect : Instance<BlenderMeshSelect>, IStatusProvider
{
    [Input(Guid = "12bcfca2-ebbc-55f5-a75c-dd53ab356690")]
    public readonly InputSlot<SceneSetup> Scene = new();

    [Input(Guid = "f47fce56-d58d-51c6-b598-f62d33ce570d")]
    public readonly InputSlot<int> PrimitiveIndex = new();

    [Output(Guid = "62d60908-5865-55cc-b0c6-821b3008c913", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<MeshBuffers> Mesh = new();

    public BlenderMeshSelect() => Mesh.UpdateAction = Update;

    private void Update(EvaluationContext context)
    {
        var scene = Scene.GetValue(context);
        var index = PrimitiveIndex.GetValue(context);
        Mesh.Value = scene != null && index >= 0 && index < scene.Dispatches.Count
                         ? scene.Dispatches[index].MeshBuffers
                         : null!;
        var names = new List<string>();
        if (scene != null)
            foreach (var root in scene.RootNodes)
                CollectNames(root, names);
        _status = index >= 0 && index < names.Count
                      ? $"Primitive {index + 1}/{names.Count}: {names[index]}"
                      : $"Primitive index {index} is outside 0..{Math.Max(0, names.Count - 1)}";
    }

    private static void CollectNames(SceneSetup.SceneNode node, List<string> names)
    {
        if (node.MeshBuffers != null)
            names.Add(node.Name ?? string.Empty);
        foreach (var child in node.ChildNodes)
            CollectNames(child, names);
    }

    IStatusProvider.StatusLevel IStatusProvider.GetStatusLevel() => IStatusProvider.StatusLevel.Success;
    string IStatusProvider.GetStatusMessage() => _status;
    private string _status = string.Empty;
}
