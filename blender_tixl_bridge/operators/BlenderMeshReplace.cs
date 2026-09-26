#nullable enable
using System;
using T3.Core.DataTypes;
using T3.Core.Operator;
using T3.Core.Operator.Attributes;
using T3.Core.Operator.Slots;

namespace PrismalLabs.BlenderExport;

/// <summary>Replaces one animated draw primitive while retaining its transform and material.</summary>
[Guid("789071a8-bd89-51bf-9f47-b942db0fa875")]
public sealed class BlenderMeshReplace : Instance<BlenderMeshReplace>
{
    [Input(Guid = "65a28b5a-632d-566b-ad67-399cb9e4f515")]
    public readonly InputSlot<SceneSetup> Scene = new();

    [Input(Guid = "259ad7a2-2034-5836-a17a-707ad5905d6d")]
    public readonly InputSlot<MeshBuffers> Mesh = new();

    [Input(Guid = "84dc72f4-f0b9-5107-a821-e388dff9b4b3")]
    public readonly InputSlot<int> PrimitiveIndex = new();

    [Output(Guid = "3012e73d-3204-59e0-a39c-b53aec53de67", DirtyFlagTrigger = DirtyFlagTrigger.Animated)]
    public readonly Slot<SceneSetup> Result = new();

    private readonly SceneSetup _result = new();

    public BlenderMeshReplace() => Result.UpdateAction = Update;

    private void Update(EvaluationContext context)
    {
        var scene = Scene.GetValue(context);
        var mesh = Mesh.GetValue(context);
        var index = PrimitiveIndex.GetValue(context);
        if (scene == null || mesh == null || index < 0 || index >= scene.Dispatches.Count
            || ReferenceEquals(mesh, scene.Dispatches[index].MeshBuffers))
        {
            Result.Value = scene!;
            return;
        }

        _result.Dispatches.Clear();
        for (var i = 0; i < scene.Dispatches.Count; i++)
        {
            var original = scene.Dispatches[i];
            if (i != index)
            {
                _result.Dispatches.Add(original);
                continue;
            }
            var sameVertexCount = mesh.VertexBuffer?.Srv?.Description.Buffer.ElementCount
                                  == original.MeshBuffers?.VertexBuffer?.Srv?.Description.Buffer.ElementCount;
            _result.Dispatches.Add(new SceneSetup.SceneDrawDispatch
            {
                MeshBuffers = mesh,
                VertexCount = original.VertexCount == 0 ? 0 : mesh.FaceCount * 3,
                VertexStartIndex = 0,
                Material = original.Material,
                CombinedTransform = original.CombinedTransform,
                ChunkIndex = ReferenceEquals(mesh.ChunkDefsBuffer, original.MeshBuffers?.ChunkDefsBuffer)
                                 ? original.ChunkIndex : 0,
                Scale = original.Scale,
                SkinWeights = sameVertexCount ? original.SkinWeights : null,
                SkeletonIndex = sameVertexCount ? original.SkeletonIndex : -1,
            });
        }
        Result.Value = _result;
    }
}
